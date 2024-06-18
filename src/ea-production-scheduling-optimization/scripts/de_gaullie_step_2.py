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

# Ranges
model.P = pyo.Set(initialize = df_prod_time["product_flavor"].unique())
model.L = pyo.Set(initialize = df_capacity["Line"].unique())

# Data
PT_data = {
    (p,l): df_prod_time[df_prod_time["product_flavor"] == p][l].values[0]
    for p in model.P for l in model.L
}
Line_Capacity_data = {
    l: df_capacity[df_capacity["Line"] == l]["Capacity"].values[0] for l in model.L
}

# Parameters
model.PT_pl = pyo.Param(model.P, model.L, initialize = PT_data)
model.LC_l = pyo.Param(model.L, initialize = Line_Capacity_data)

# Decision Variables
model.x_pl = pyo.Var(model.P,model.L, domain = pyo.Binary)


def constraint_1(model,p):
    lhs = pyo.quicksum(model.x_pl[p,l] for l in model.L)
    rhs = 1
    return lhs == rhs
model.c_1 = pyo.Constraint(model.P,rule = constraint_1)

def constraint_2(model,l):
    lhs = pyo.quicksum(model.PT_pl[p,l]*model.x_pl[p,l] for p in model.P)
    rhs = 0.85*model.LC_l[l]
    return lhs <= rhs
model.c_2 = pyo.Constraint(model.L, rule = constraint_2)

def constraint_3(model,l):
    lhs = pyo.quicksum(model.PT_pl[p,l]*model.x_pl[p,l] for p in model.P)
    rhs = 0.15*model.LC_l[l]
    return lhs >= rhs
model.c_3 = pyo.Constraint(model.L, rule = constraint_3)

obj_expr = pyo.quicksum(model.PT_pl[p,l]*model.x_pl[p,l] for p in model.P for l in model.L)

model.obj = pyo.Objective(expr=obj_expr,sense=pyo.minimize)

model.write("models/product_assignment_and_sequencing.lp",io_options={'symbolic_solver_labels': True})

# solver = pyo.SolverFactory('gurobi')
solver = pyo.SolverFactory('cbc',executable=r'.\CoinAll-1.6.0-win64-intel11.1\CoinAll-1.6.0-win64-intel11.1\cbc.exe')
# solver.options['MIPGap'] = 0.1
# solver.options['TimeLimit'] = 100
solver.options['seconds'] = 600
result = solver.solve(model, tee=True)

# Store Output
product_list,line_list,val_list = [], [], []
for i in model.x_pl:
    product_list.append(i[0])
    line_list.append(i[1])
    val_list.append(model.x_pl[i].value)
df_assignment = pd.DataFrame({
    "product_flavor":product_list,
    "Line":line_list,
    "assignment_flag":val_list
})

df_assignment = pd.pivot_table(
    df_assignment, 
    index = "product_flavor", 
    columns="Line", 
    values="assignment_flag",
    aggfunc="max"
).reset_index().merge(
    df_prod_time[["product_flavor","Flavor"]],
    on = "product_flavor",
    how = "left"
)


cols_a = df_assignment[df_assignment["A"] == 1]["Flavor"].unique()

df_co_grid[cols_a]


