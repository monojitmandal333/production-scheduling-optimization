import pyomo.environ as pyo
import numpy as np
import pandas as pd
import os
import pickle
import datetime as dt

data_location = "AL_CHEWY_data.xlsx"
df_cot = pd.read_excel(data_location, sheet_name = "CO")
# df_cot.columns = [f"product_{i}" if i != 0 else df_cot.columns[i] for i in range(len(df_cot.columns))]
df_cot.columns = [f"product_{col}" if col != "from" else col for col in df_cot.columns]
df_cot = pd.wide_to_long(
    df_cot,stubnames="product_", i= "from", j="to_material_cd").reset_index().rename(columns = {"product_":"co_time"})
df_cot = df_cot.rename(columns={"to_material_cd":"to"})
# df_map = pd.read_excel(data_location, sheet_name = "mapping")
# df_cot = df_cot.merge(
#     df_map.rename(columns = {"material_cd":"to_material_cd","product_name":"to"}), 
#     how = "left",
#     on = "to_material_cd")[["from","to","co_time"]]
df_dos = pd.read_excel(data_location, sheet_name = "inventory")
df_demand = pd.read_excel(data_location, sheet_name = "demand")
df_lr = pd.read_excel(data_location, sheet_name = "line_rate")
df_gm = pd.read_excel(data_location, sheet_name="gross_margin")

df_product_mapping = pd.read_excel(data_location, sheet_name="product_mapping")
df_fw_mapping = pd.read_excel(data_location, sheet_name="FW_mapping")

model = pyo.ConcreteModel()
model.n_timeframes = 52

# Ranges
model.T = pyo.RangeSet(0, model.n_timeframes-1)
model.D = pyo.RangeSet(0, model.n_timeframes*7-1)
model.P = pyo.Set(initialize = df_cot["from"].unique())
model.T_minus_1 = pyo.RangeSet(0,model.n_timeframes-2)
model.D_minus_1 = pyo.RangeSet(0,model.n_timeframes*7-2)

cf = 10000
# Data
COT_data = {
    (p,q):df_cot[(df_cot["from"] == p) & (df_cot["to"] == q)]["co_time"].to_numpy()[0] 
    for p in model.P for q in model.P
}
demand = {(p,t): df_demand[df_demand["material_cd"] == p][t].to_numpy()[0]/cf for p in model.P for t in model.T}
LR_data = {p: df_lr[df_lr["material_cd"] == p]["line_rate_per_day"].to_numpy()[0]/cf for p in model.P}
beg_inv = {p:df_dos[df_dos["material_cd"] == p]["beginning_inventory"].to_numpy()[0]/cf for p in model.P}
safety_stock = {p:df_dos[df_dos["material_cd"] == p]["safety_stock"].to_numpy()[0]/cf for p in model.P}
gross_margin = {p:df_gm[df_gm["material_cd"] == p]["gross_margin"].to_numpy()[0] for p in model.P}
penalty_cost = {p:gross_margin[p] for p in model.P}
holding_cost = {p:0.07/52 for p in model.P}


# Parameters
model.COT_pq = pyo.Param(model.P, model.P,initialize = COT_data)
model.D_pt = pyo.Param(model.P,model.T, initialize = demand)
model.LR_p = pyo.Param(model.P, initialize = LR_data)
model.BINV = pyo.Param(model.P, initialize = beg_inv)
model.SS = pyo.Param(model.P, initialize = safety_stock)

# profit_margin = 0.5
# penalty_cost = 1
# holding_cost = 0.01

# Decision Variables
model.X_pt = pyo.Var(model.P,model.D, domain = pyo.Binary)
model.W_pqt = pyo.Var(model.P,model.P,model.D,domain = pyo.Binary)
model.y_pt_plus = pyo.Var(model.P,model.T,domain = pyo.NonNegativeReals)
model.y_pt_minus = pyo.Var(model.P,model.T,domain = pyo.NonNegativeReals)
model.a_pt = pyo.Var(model.P,model.D,domain = pyo.NonNegativeReals)


def constraint_1a(model,p,q,t):
    lhs = model.W_pqt[p,q,t]
    rhs = model.X_pt[p,t] + model.X_pt[q,t+1] - 1
    return lhs >= rhs
model.c_1a = pyo.Constraint(model.P,model.P, model.D_minus_1, rule=constraint_1a)

def constraint_1b(model,p,q,t):
    lhs = model.W_pqt[p,q,t]
    rhs = model.X_pt[p,t]
    return lhs <= rhs
model.c_1b = pyo.Constraint(model.P,model.P, model.D, rule = constraint_1b)

def constraint_1c(model,p,q,t):
    lhs = model.W_pqt[p,q,t]
    rhs = model.X_pt[q,t+1]
    return lhs <= rhs
model.c_1c = pyo.Constraint(model.P,model.P, model.D_minus_1, rule=constraint_1c)

def constraint_2(model,t):
    lhs = pyo.quicksum(model.X_pt[p,t] for p in model.P)
    rhs = 1
    return lhs == rhs
model.c_2 = pyo.Constraint(model.D,rule = constraint_2)

def constraint_4(model,p,t):
    lhs = model.a_pt[p,t]
    rhs = model.LR_p[p]*model.X_pt[p,t]
    return lhs <= rhs
model.c_4 = pyo.Constraint(model.P,model.D,rule = constraint_4)

def constraint_5(model,p,t):
    lhs = pyo.quicksum(model.a_pt[p,i] for i in np.array(model.D)[:(t+1)*7]) -\
          pyo.quicksum(model.D_pt[p,i] for i in np.array(model.T)[:(t+1)]) +\
            model.BINV[p] - model.SS[p]
    rhs = model.y_pt_plus[p,t] - model.y_pt_minus[p,t]
    return lhs == rhs
model.c_5 = pyo.Constraint(model.P,model.T,rule = constraint_5)


obj_expr = pyo.quicksum(
        model.COT_pq[p,q]*model.W_pqt[p,q,t]*(1/24)*model.LR_p[p]*gross_margin[p] for p in model.P for q in model.P for t in model.D) + \
    pyo.quicksum(
        holding_cost[p]*model.y_pt_plus[p,t] + penalty_cost[p]*model.y_pt_minus[p,t] for p in model.P for t in model.T)

model.obj = pyo.Objective(expr=obj_expr,sense=pyo.minimize)

model.write("pyomo_model.lp",io_options={'symbolic_solver_labels': True})


solver = pyo.SolverFactory('cbc',executable=r'.\CoinAll-1.6.0-win64-intel11.1\CoinAll-1.6.0-win64-intel11.1\cbc.exe')
# n_threads = os.cpu_count()
# solver.options['threads'] = n_threads-1

# Set a timeout after that a solution is returned
time_sec = 8*60*60
solver.options['seconds'] = time_sec
result = solver.solve(model, tee=True)

# model = pickle.load(open("model_20230428185136.sav","rb"))

df_X = pd.DataFrame(columns = model.D, index = model.P)
for i in model.X_pt:
    df_X.loc[i[0]][i[1]] = int(model.X_pt[i].value)
df_X = df_X.reset_index().rename(columns = {"index":"material_cd"})
print(df_X)

df_a = pd.DataFrame(columns = model.D, index = model.P)
for i in model.a_pt:
    df_a.loc[i[0]][i[1]] = int(model.a_pt[i].value*cf)
df_a = df_a.reset_index().rename(columns = {"index":"material_cd"})
print(df_a)

p_list,q_list,t_list,co_flag_list,co_time_list = [], [], [], [], []
for i in model.W_pqt:
    p_list.append(i[0])
    q_list.append(i[1])
    t_list.append(i[2])
    val = model.W_pqt[i].value
    if ((i[0] != i[1]) & (val == 1)):
        co_flag_list.append(True)
        co_time_list.append(COT_data[i[0],i[1]])
    else:
        co_flag_list.append(False)
        co_time_list.append(0)

df_W = pd.DataFrame({"from_material_cd":p_list,
                     "to_material_cd":q_list,
                     "period":t_list,
                     "CO_Flag":co_flag_list,
                     "CO_Time":co_time_list
                     })
df_W = df_W.merge(
    df_product_mapping.rename(columns = {"material_cd":"from_material_cd","product_name":"from_product_name"}),
    how = "left", on = "from_material_cd")
df_W = df_W.merge(
    df_product_mapping.rename(columns = {"material_cd":"to_material_cd","product_name":"to_product_name"}),
    how = "left", on = "to_material_cd")
# df_W = df_W.merge(df_fw_mapping,how = "left",on = "week_nbr")
df_W = df_W[
    ["from_material_cd","to_material_cd","from_product_name",
     "to_product_name","period","CO_Flag","CO_Time"
    ]
]
print(df_W)

p_list, t_list, val_list = [], [], []
for i in model.y_pt_plus:
    p_list.append(i[0])
    t_list.append(i[1])
    val_list.append(model.y_pt_plus[i].value*cf)
df_y_pt_plus = pd.DataFrame({"material_cd": p_list,
                             "week_nbr":t_list,
                             "excess_inventory":val_list})

p_list, t_list, val_list = [], [], []
for i in model.y_pt_plus:
    p_list.append(i[0])
    t_list.append(i[1])
    val_list.append(model.y_pt_minus[i].value*cf)
df_y_pt_minus = pd.DataFrame({"material_cd": p_list,
                              "week_nbr":t_list,
                              "short_inventory":val_list})

df_y = df_y_pt_plus.merge(df_y_pt_minus,how = "left", on = ["material_cd","week_nbr"])
df_y = df_y.merge(df_product_mapping, how = "left", on = "material_cd")
df_y = df_y.merge(df_fw_mapping,how = "left",on = "week_nbr")

# Master Production Schedule
df_mps_inventory = df_y.copy()
df_mps_inventory = df_mps_inventory.merge(df_dos[["material_cd","safety_stock"]], how="left",on = "material_cd")
df_mps_inventory["inventory"] = df_mps_inventory["safety_stock"] + \
    df_mps_inventory["excess_inventory"] - df_mps_inventory["short_inventory"]
df_mps_inventory.head()

df_mps_production = df_a.copy()
for i in range(model.n_timeframes):
    df_mps_production[f"production_{str(i)}"] = df_mps_production[
        list(range(i, (i + 1) * 7))
    ].sum(axis=1)
df_mps_production = df_mps_production[
    ["material_cd"] + [f"production_{str(i)}" for i in range(model.n_timeframes)]
]
# df_mps_production.columns = [f"production_{col}" if col != "material_cd" else col for col in df_mps_production.columns ]
df_mps_production = pd.wide_to_long(
    df_mps_production,
    stubnames="production", 
    i= "material_cd", j="week_nbr",sep='_').reset_index()
# df_mps_production = df_mps_production.merge(df_lr,how = "left", on = "material_cd")
# df_mps_production["production"] = df_mps_production["production"]*df_mps_production["line_rate_per_day"]*7
df_mps_production = df_mps_production[["material_cd","week_nbr","production"]]

df_mps_demand = df_demand.copy()
df_mps_demand.columns = [f"demand_{col}" if col != "material_cd" else col for col in df_mps_demand.columns ]
df_mps_demand = pd.wide_to_long(
    df_mps_demand,
    stubnames="demand", 
    i= "material_cd", j="week_nbr",sep='_').reset_index()

df_mps = df_mps_production.merge(df_mps_demand,how = "left",on = ["material_cd","week_nbr"])
df_mps = df_mps.merge(df_mps_inventory,how = "left",on = ["material_cd","week_nbr"])
df_mps.head()


now = dt.datetime.now().strftime('%Y%m%d%H%M%S')
with pd.ExcelWriter(f"output_{now}.xlsx") as writer:
    df_X.to_excel(writer, sheet_name='week wise product')
    df_W.to_excel(writer, sheet_name='product changeover')
    df_y.to_excel(writer, sheet_name= "inventory")
    df_mps.to_excel(writer,sheet_name="MPS")

# file_name = f"model_{now}.sav"
# pickle.dump(model,open(file_name,"wb"))