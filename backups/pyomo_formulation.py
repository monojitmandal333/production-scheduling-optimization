from __future__ import division
import pyomo.environ as pyo
import numpy as np
import pandas as pd

# model = pyo.AbstractModel()
model = pyo.ConcreteModel()

model.n_timeframes = 52
model.n_products = 4

# Ranges
model.T = pyo.RangeSet(0, model.n_timeframes-1)
model.P = pyo.RangeSet(0, model.n_products-1)
model.T_minus_1 = pyo.RangeSet(0,model.n_timeframes-2)


# # Range.
# P = np.array(model.P)
# T = np.array(model.T)
# T_minus_1 = T[:len(T)-1]

df_cot = np.array(pd.read_excel("data.xlsx", sheet_name = "CO").set_index("From"))
df_dos = np.array(pd.read_excel("data.xlsx", sheet_name = "DOS").set_index("product_name"))
df_idos = np.array(pd.read_excel("data.xlsx", sheet_name = "IDOS").set_index("product_name"))
df_demand = np.array(pd.read_excel("data.xlsx", sheet_name = "demand").set_index("product_name"))
df_lr = np.array(pd.read_excel("data.xlsx", sheet_name = "line_rate").set_index("product_name"))

# Data
COT_data = {(p,q):df_cot[p][q] for p in model.P for q in model.P}
DOS_data = {(p,t):df_dos[p][0] for p in model.P for t in model.T}
OR_data = {p:df_demand[p][0]/52 for p in model.P}
LR_data = {p:df_lr[p][0]*7 for p in model.P}

# Parameters
model.COT_pq = pyo.Param(model.P, model.P,initialize = COT_data)
model.DOS_pt = pyo.Param(model.P, model.T, initialize = DOS_data)
model.OR_p = pyo.Param(model.P, initialize = OR_data)
model.LR_p = pyo.Param(model.P, initialize = LR_data)

# data = {"COT_pq":COT_data,"DOS_pt":DOS_data,"OR_p":OR_data,"TR_p":TR_data}
# instance = model.create_instance(data)

# Decision Variables
model.X_pt = pyo.Var(model.P,model.T, domain=pyo.Binary)
model.W_pqt = pyo.Var(model.P,model.P,model.T,domain = pyo.Binary)

def constraint_1a(model,p,q,t):
    lhs = model.W_pqt[p,q,t]
    rhs = model.X_pt[p,t] + model.X_pt[q,t+1] - 1
    return lhs >= rhs
model.c_1a = pyo.Constraint(model.P,model.P, model.T_minus_1, rule=constraint_1a)

def constraint_1b(model,p,q,t):
    lhs = model.W_pqt[p,q,t]
    rhs = model.X_pt[p,t]
    return lhs <= rhs
model.c_1b = pyo.Constraint(model.P,model.P, model.T, rule = constraint_1b)

def constraint_1c(model,p,q,t):
    lhs = model.W_pqt[p,q,t]
    rhs = model.X_pt[q,t+1]
    return lhs <= rhs
model.c_1c = pyo.Constraint(model.P,model.P, model.T_minus_1, rule=constraint_1a)

def constraint_2(model,t):
    lhs = pyo.quicksum(model.X_pt[p,t] for p in model.P)
    rhs = 1
    return lhs == rhs
model.c_2 = pyo.Constraint(model.T,rule = constraint_2)

def constraint_3(model,p):
    lhs = pyo.quicksum(model.X_pt[p,t] for t in model.T)
    rhs = model.OR_p[p]*model.n_timeframes/model.LR_p[p]
    return lhs >= rhs
model.c_3 = pyo.Constraint(model.P,rule = constraint_3)

obj_expr = pyo.quicksum(
    model.COT_pq[p,q]*model.W_pqt[p,q,t] for p in model.P for q in model.P for t in model.T)
    #     pyo.quicksum(
    #         (pyo.quicksum(model.X_pt[p,t] for t in model.T)- model.OR_p[p]*model.n_timeframes/model.LR_p[p]) 
    #     for p in model.P
    # )
model.obj = pyo.Objective(expr=obj_expr,sense=pyo.minimize)

# @model.Constraint(model.P,model.P,model.T_minus_1)
# def constraint_1_a(m,p,q,t):
#     return m.W_pqt[p,q,t] >= m.X_pt[p,t] + m.X_pt[q,t+1]-1

# @model.Constraint(model.P,model.P,model.T_minus_1)
# def constraint_1_b(m,p,q,t):
#     return m.W_pqt[p,q,t] <= m.X_pt[p,t]

# @model.Constraint(model.P,model.P,model.T_minus_1)
# def constraint_1_c(m,p,q,t):
#     return m.W_pqt[p,q,t] <= m.X_pt[q,t]

# @model.Constraint(model.T)
# def constraint_2(m, t):
#     return sum([m.X_pt[p,t] for p in m.P]) == 1

# @model.Constraint(model.P)
# def constraint_3(m,p):
#     lhs = sum(m.X_pt[p,t] for t in m.T)
#     rhs = m.OR_p[p]*m.n_timeframes/m.LR_p[p]
#     return lhs >= rhs


model.write("pyomo_model.lp",io_options={'symbolic_solver_labels': True})
# solver = pyo.SolverFactory('cplex')
solver = pyo.SolverFactory('cbc',executable=r'.\CoinAll-1.6.0-win64-intel11.1\CoinAll-1.6.0-win64-intel11.1\cbc.exe')
result = solver.solve(model, tee=True)

# df_X = pd.DataFrame()
# print("Print values for all variables")
# for v in model.component_data_objects(pyo.Var):
#   print (str(v)[:4], v.value)

df_X = pd.DataFrame(columns = model.T, index = model.P)
for i in model.X_pt:
    df_X.loc[i[0]][i[1]] = int(model.X_pt[i].value)
print(df_X)

df_X.to_csv("optimal_solution_X.csv",index = False)

p_list,q_list,t_list,val_list = list(),list(),list(),list()
for i in model.W_pqt:
    p_list.append(i[0])
    q_list.append(i[1])
    t_list.append(i[2])
    val_list.append(model.W_pqt[i].value)
df_W = pd.DataFrame({"from_product":p_list,
                     "to_product":q_list,
                     "timeframe":t_list,
                     "value":val_list})
print(df_W)
df_W.to_csv("optimal_solution_W.csv", index = False)
