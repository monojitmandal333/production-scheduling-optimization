import pyomo.environ as pyo
import numpy as np
import pandas as pd
import os
import pickle
import datetime as dt

file_path = "Input/product_assignment_sequencing_by_line.xlsx"

df_prod_time = pd.read_excel(io = file_path,sheet_name="production_time")
df_capacity = pd.read_excel(io = file_path, sheet_name = "capacity")
df_co_grid = pd.read_excel(io = file_path,sheet_name="co_grid")

df_prod_time["product_flavor"] = df_prod_time["Product"] + "-" + df_prod_time["Flavor"]

model = pyo.ConcreteModel()
model.M = 10000000000
model.n_products = 40
model.n_lines = 4

# Ranges
model.P = pyo.Set(initialize = df_prod_time["product_flavor"].unique()[:model.n_products])
model.P_except_start = pyo.Set(initialize = df_prod_time["product_flavor"].unique()[1:model.n_products])
model.L = pyo.Set(initialize = df_capacity["Line"].unique()[:model.n_lines])

# Data
COT_data = {
    (p,q): df_co_grid[df_co_grid["From"] == p][q].values[0]
    for p in model.P for q in model.P
}
PT_data = {
    (p,l): df_prod_time[df_prod_time["product_flavor"] == p][l].values[0]
    for p in model.P for l in model.L
}
Line_Capacity_data = {
    l: df_capacity[df_capacity["Line"] == l]["Capacity"].values[0] for l in model.L
}

# Parameters
model.COT_pq = pyo.Param(model.P, model.P,initialize = COT_data)
model.PT_pl = pyo.Param(model.P, model.L, initialize = PT_data)

# Decision Variables
model.x_pl = pyo.Var(model.P,model.L, domain = pyo.Binary)
model.y_pql = pyo.Var(model.P,model.P,model.L, domain = pyo.Binary)
model.LC_l = pyo.Param(model.L, initialize = Line_Capacity_data)
model.u_pl = pyo.Var(model.P, model.L, domain = pyo.PositiveIntegers)
model.z_l = pyo.Var(model.L, domain = pyo.Integers)
model.w_pql = pyo.Var(model.P,model.P,model.L, domain = pyo.Integers)


def constraint_1(model,p,q,l):
    lhs = model.y_pql[p,q,l]
    rhs = model.x_pl[p,l]
    return lhs <= rhs
model.c_1 = pyo.Constraint(model.P,model.P, model.L, rule = constraint_1)

def constraint_2(model,p,q,l):
    lhs = model.y_pql[p,q,l]
    rhs = model.x_pl[q,l]
    return lhs <= rhs
model.c_2 = pyo.Constraint(model.P,model.P, model.L, rule=constraint_2)

# def constraint_3(model,p):
#     lhs = pyo.quicksum(model.y_pql[p,q,l] for q in model.P for l in model.L)
#     rhs = 1
#     return lhs == rhs
# model.c_3 = pyo.Constraint(model.P,rule = constraint_3)

# def constraint_4(model,q):
#     lhs = pyo.quicksum(model.y_pql[p,q,l] for p in model.P for l in model.L)
#     rhs = 1
#     return lhs == rhs
# model.c_4 = pyo.Constraint(model.P,rule = constraint_4)

def constraint_5a(model,l):
    lhs = model.z_l[l]
    rhs = pyo.quicksum(model.x_pl[p,l] for p in model.P)
    return lhs == rhs
model.c_5a = pyo.Constraint(model.L,rule = constraint_5a)

def constraint_5b(model,p,q,l):
    lhs = model.w_pql[p,q,l]
    rhs = model.M*model.y_pql[p,q,l]
    return lhs <= rhs
model.c_5b = pyo.Constraint(model.P, model.P,model.L,rule = constraint_5b)

def constraint_5c(model,p,q,l):
    lhs = model.w_pql[p,q,l]
    rhs = model.z_l[l] - (1 - model.y_pql[p,q,l])*model.M
    return lhs >= rhs
model.c_5c = pyo.Constraint(model.P, model.P,model.L,rule = constraint_5c)

def constraint_5d(model,p,q,l):
    lhs = model.w_pql[p,q,l]
    rhs = model.z_l[l]
    return lhs <= rhs
model.c_5d = pyo.Constraint(model.P, model.P,model.L,rule = constraint_5d)

def constraint_5e(model,p,q,l):
    lhs = model.u_pl[p,l] - model.u_pl[q,l] + model.w_pql[p,q,l]
    rhs = model.z_l[l] - 1
    return lhs <= rhs
model.c_5e = pyo.Constraint(model.P_except_start, model.P_except_start,model.L,rule = constraint_5e)

def constraint_5f(model,p,q,l):
    lhs = model.w_pql[p,q,l]
    rhs = 0
    return lhs >= rhs
model.c_5f = pyo.Constraint(model.P, model.P,model.L,rule = constraint_5f)

def constraint_6(model,p,l):
    lhs = model.u_pl[p,l]
    rhs = model.M*model.x_pl[p,l]
    return lhs <= rhs
model.c_6 = pyo.Constraint(model.P_except_start, model.L, rule = constraint_6)

def constraint_7(model,p):
    lhs = pyo.quicksum(model.x_pl[p,l] for l in model.L)
    rhs = 1
    return lhs == rhs
model.c_7 = pyo.Constraint(model.P, rule = constraint_7)

obj_expr = pyo.quicksum(
    model.COT_pq[p,q]*model.y_pql[p,q,l] 
    for p in model.P for q in model.P for l in model.L
) + pyo.quicksum(
    model.PT_pl[p,l]*model.x_pl[p,l]
    for p in model.P for l in model.L
)

model.obj = pyo.Objective(expr=obj_expr,sense=pyo.minimize)

model.write("models/product_assignment_and_sequencing.lp",io_options={'symbolic_solver_labels': True})

# solver = pyo.SolverFactory('gurobi')
solver = pyo.SolverFactory('cbc',executable=r'.\CoinAll-1.6.0-win64-intel11.1\CoinAll-1.6.0-win64-intel11.1\cbc.exe')
# solver.options['MIPGap'] = 0.1
# solver.options['TimeLimit'] = 100
solver.options['seconds'] = 600
result = solver.solve(model, tee=True)


for i in model.x_pl:
    print(i,model.x_pl[i].value)
