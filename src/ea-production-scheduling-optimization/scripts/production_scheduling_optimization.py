import pyomo.environ as pyo
import numpy as np
import pandas as pd
import os
import pickle
import datetime as dt

# Data Import------------------------------------------------------------------------------------------------------------
data_location = "input/F23_AL_CHEWY.xlsx"
df_cot = pd.read_excel(data_location, sheet_name = "CO_Matrix")
df_cot.columns = [f"product_{col}" if col != "from" else col for col in df_cot.columns]
df_cot = pd.wide_to_long(
    df_cot,stubnames="product_", i= "from", j="to_material_cd"
).reset_index().rename(columns = {"product_":"co_time"})
df_cot = df_cot.rename(columns={"to_material_cd":"to"})
df_dos = pd.read_excel(data_location, sheet_name = "Beg_Inv_SS")
df_demand = pd.read_excel(data_location, sheet_name = "demand")
df_lr = pd.read_excel(data_location, sheet_name = "line_rate")
df_gm = pd.read_excel(data_location, sheet_name="gross_margin")
df_product_mapping = pd.read_excel(data_location, sheet_name="product_mapping")
df_fw_mapping = pd.read_excel(data_location, sheet_name="FW_mapping")
df_production_non_AL = pd.read_excel(data_location, sheet_name="production")
df_act_production = pd.read_excel(data_location, sheet_name="actual_production")
df_inventory = pd.read_excel(data_location, sheet_name="Inventory")
df_act_CO = pd.read_excel(data_location,sheet_name="actual_CO")

# Defining Model----------------------------------------------------------------------------------------------------------
model = pyo.ConcreteModel()

# Defining Ranges----------------------------------------------------------------------------------------------------------
model.n_timeframes = 52
model.T = pyo.RangeSet(0, model.n_timeframes-1)
model.D = pyo.RangeSet(0, model.n_timeframes*7-1)
model.P = pyo.Set(initialize = df_cot["from"].unique())
model.T_minus_1 = pyo.RangeSet(0,model.n_timeframes-2)
model.D_minus_1 = pyo.RangeSet(0,model.n_timeframes*7-2)

# Conversion Factor to reduce problem size---------------------------------------------------------------------------------
cf = 100000

# Data for Model Parameters------------------------------------------------------------------------------------------------
COT_data = {
    (p,q):df_cot[(df_cot["from"] == p) & (df_cot["to"] == q)]["co_time"].to_numpy()[0] 
    for p in model.P for q in model.P
}
demand = {
    (p,t): 0 if (len(df_demand[(df_demand["material_cd"] == p) & (df_demand["week_nbr"] == t)]) == 0) 
    else df_demand[(df_demand["material_cd"] == p) & (df_demand["week_nbr"] == t)]["demand"].to_numpy()[0]/cf 
    for p in model.P for t in model.T}
LR_data = {p: df_lr[df_lr["material_cd"] == p]["line_rate_per_day"].to_numpy()[0]/cf for p in model.P}
beg_inv = {p:df_dos[df_dos["material_cd"] == p]["beginning_inventory"].to_numpy()[0]/cf for p in model.P}
safety_stock = {p:df_dos[df_dos["material_cd"] == p]["safety_stock"].to_numpy()[0]/cf for p in model.P}
inventory_capacity = {p:df_dos[df_dos["material_cd"] == p]["inv_capacity"].to_numpy()[0]/cf for p in model.P}
gross_margin = {p:df_gm[df_gm["material_cd"] == p]["gross_margin"].to_numpy()[0] for p in model.P}
production_non_AL = {
    (p,t): 0 if (len(df_production_non_AL[
        (df_production_non_AL["material_cd"] == p) & 
        (df_production_non_AL["week_nbr"] == t)]) == 0) 
    else df_production_non_AL[
        (df_production_non_AL["material_cd"] == p) & 
        (df_production_non_AL["week_nbr"] == t)]["actual_production_non_AL"].to_numpy()[0]/cf 
    for p in model.P for t in model.T}
production_AL = {
    p: sum(df_act_production[df_act_production["material_cd"] == p]["production_actual"])/cf for p in model.P
}
penalty_cost = {p:gross_margin[p] for p in model.P}
overflow_cost = {p:gross_margin[p] for p in model.P}
holding_cost = {p:0.09/52 for p in model.P}

# Model Parameters--------------------------------------------------------------------------------------------------------
model.COT_pq = pyo.Param(model.P, model.P,initialize = COT_data)
model.D_pt = pyo.Param(model.P,model.T, initialize = demand)
model.LR_p = pyo.Param(model.P, initialize = LR_data)
model.BINV = pyo.Param(model.P, initialize = beg_inv)
model.SS = pyo.Param(model.P, initialize = safety_stock)
model.INV_CAP = pyo.Param(model.P, initialize = inventory_capacity)
model.production_non_AL = pyo.Param(model.P,model.T, initialize = production_non_AL)
model.production_AL = pyo.Param(model.P, initialize = production_AL)


# Decision Variables-----------------------------------------------------------------------------------------------------
model.X_pt = pyo.Var(model.P,model.D, domain = pyo.Binary)
model.W_pqt = pyo.Var(model.P,model.P,model.D,domain = pyo.Binary)
model.y_pt_plus = pyo.Var(model.P,model.T,domain = pyo.NonNegativeReals)
model.y_pt_minus = pyo.Var(model.P,model.T,domain = pyo.NonNegativeReals)
model.overflow_pt_plus = pyo.Var(model.P,model.T,domain = pyo.NonNegativeReals)
model.overflow_pt_minus = pyo.Var(model.P,model.T,domain = pyo.NonNegativeReals)
model.a_pt = pyo.Var(model.P,model.D,domain = pyo.NonNegativeReals)

# Constraints--------------------------------------------------------------------------------------------------------------
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
    return lhs <= rhs
model.c_2 = pyo.Constraint(model.D,rule = constraint_2)

def constraint_3(model,t):
    lhs = pyo.quicksum(model.X_pt[p,t] for p in model.P)
    rhs = pyo.quicksum(model.X_pt[p,(t+1)] for p in model.P)
    return lhs >= rhs
model.c_3 = pyo.Constraint(model.D_minus_1,rule = constraint_3)

def constraint_4(model,p,t):
    lhs = model.a_pt[p,t]
    rhs = model.LR_p[p]*model.X_pt[p,t]
    return lhs <= rhs
model.c_4 = pyo.Constraint(model.P,model.D,rule = constraint_4)

def constraint_5(model,p,t):
    lhs = pyo.quicksum(model.a_pt[p,i] for i in np.array(model.D)[:(t+1)*7]) +\
            pyo.quicksum(model.production_non_AL[p,i] for i in np.array(model.T)[:(t+1)]) -\
            pyo.quicksum(model.D_pt[p,i] for i in np.array(model.T)[:(t+1)]) +\
            model.BINV[p] - model.SS[p]
    rhs = model.y_pt_plus[p,t] - model.y_pt_minus[p,t]
    return lhs == rhs
model.c_5 = pyo.Constraint(model.P,model.T,rule = constraint_5)

def constraint_6(model,p,t):
    lhs = pyo.quicksum(model.a_pt[p,i] for i in np.array(model.D)[:(t+1)*7]) +\
            pyo.quicksum(model.production_non_AL[p,i] for i in np.array(model.T)[:(t+1)]) -\
            pyo.quicksum(model.D_pt[p,i] for i in np.array(model.T)[:(t+1)]) +\
            model.BINV[p]- model.INV_CAP[p]
    rhs = model.overflow_pt_plus[p,t] - model.overflow_pt_minus[p,t]
    return lhs == rhs
model.c_6 = pyo.Constraint(model.P,model.T,rule = constraint_6)

def constraint_7(model,p):
    lhs = pyo.quicksum(model.a_pt[p,i] for i in np.array(model.D))
    rhs = model.production_AL[p]
    return lhs >= rhs
model.c_7 = pyo.Constraint(model.P,rule = constraint_7)

# Objective Function------------------------------------------------------------------------------------------------------
obj_expr = pyo.quicksum(
        model.COT_pq[p,q]*model.W_pqt[p,q,t]*(1/24)*model.LR_p[p]*gross_margin[p] 
        for p in model.P for q in model.P for t in model.D) + \
    pyo.quicksum(
        holding_cost[p]*model.y_pt_plus[p,t] + penalty_cost[p]*model.y_pt_minus[p,t] +\
              overflow_cost[p]*model.overflow_pt_plus[p,t] for p in model.P for t in model.T)

model.obj = pyo.Objective(expr=obj_expr,sense=pyo.minimize)

# Save Model-----------------------------------------------------------------------------------------------------------
model.write("models/production_scheduling.lp",io_options={'symbolic_solver_labels': True})

# Solve Model-----------------------------------------------------------------------------------------------------------
solver = pyo.SolverFactory('gurobi')
# solver.options['MIPGap'] = 0.1
solver.options['TimeLimit'] = 2*3600
result = solver.solve(model, tee=True)

# Save Outputs -----------------------------------------------------------------------------------------------------------
df_X = pd.DataFrame(columns = model.P, index = model.D)
for i in model.X_pt:
    df_X.loc[i[1]][i[0]] = int(model.X_pt[i].value)
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
                             "inventory_excess_plan":val_list})

p_list, t_list, val_list = [], [], []
for i in model.y_pt_plus:
    p_list.append(i[0])
    t_list.append(i[1])
    val_list.append(model.y_pt_minus[i].value*cf)
df_y_pt_minus = pd.DataFrame({"material_cd": p_list,
                              "week_nbr":t_list,
                              "inventory_shortage_plan":val_list})

p_list, t_list, val_list = [], [], []
for i in model.y_pt_plus:
    p_list.append(i[0])
    t_list.append(i[1])
    val_list.append(model.overflow_pt_plus[i].value*cf)
df_overflow = pd.DataFrame({"material_cd": p_list,
                              "week_nbr":t_list,
                              "inventory_overflow_plan":val_list})

df_y = df_y_pt_plus.merge(df_y_pt_minus,how = "left", on = ["material_cd","week_nbr"])
df_y = df_y.merge(df_overflow, how = "left", on = ["material_cd","week_nbr"])
df_y = df_y.merge(df_product_mapping, how = "left", on = "material_cd")
df_y = df_y.merge(df_fw_mapping,how = "left",on = "week_nbr")

# Master Production Schedule
df_mps_inventory = df_y.copy()
df_mps_inventory = df_mps_inventory.merge(df_dos[["material_cd","safety_stock"]], how="left",on = "material_cd")
df_mps_inventory["inventory_plan"] = df_mps_inventory["safety_stock"] + df_mps_inventory["inventory_overflow_plan"] +\
    df_mps_inventory["inventory_excess_plan"] - df_mps_inventory["inventory_shortage_plan"]
df_mps_inventory.head()

df_mps_production = df_a.copy()
for i in range(model.n_timeframes):
    df_mps_production[f"production_plan_{str(i)}"] = df_mps_production[
        list(range(i*7, (i + 1)*7))
    ].sum(axis=1)
df_mps_production = df_mps_production[
    ["material_cd"] + [f"production_plan_{str(i)}" for i in range(model.n_timeframes)]
]

df_mps_production = pd.wide_to_long(
    df_mps_production,
    stubnames="production_plan", 
    i= "material_cd", j="week_nbr",sep='_').reset_index()
df_mps_production = df_mps_production[["material_cd","week_nbr","production_plan"]]
df_mps_production = df_mps_production.merge(df_production_non_AL,how = "left", on = ["material_cd","week_nbr"])
df_mps_production = df_mps_production.fillna(0)

df_mps_demand = df_demand.copy()

df_mps = df_mps_production.merge(df_mps_demand,how = "left",on = ["material_cd","week_nbr"])
df_mps["total_production_plan"] = df_mps["production_plan"] + df_mps["actual_production_non_AL"]
df_mps = df_mps.merge(df_mps_inventory,how = "left",on = ["material_cd","week_nbr"])
df_mps = df_mps.merge(df_act_production,how = "left", on = ["material_cd","week_nbr"])
df_mps = df_mps.merge(df_inventory,how = "left", on = ["material_cd","week_nbr"])
df_mps["inventory_shortage_actual"] = df_mps["inventory_actual"] - df_mps["safety_stock"]
df_mps.head()


now = dt.datetime.now().strftime('%Y%m%d%H%M%S')
with pd.ExcelWriter(f"output/output_{now}.xlsx") as writer:
    df_X.to_excel(writer, sheet_name='week wise product')
    df_W.to_excel(writer, sheet_name='product changeover')
    df_act_CO.to_excel(writer,sheet_name = "Actual CO")
    df_y.to_excel(writer, sheet_name= "inventory")
    df_mps.to_excel(writer,sheet_name="MPS")