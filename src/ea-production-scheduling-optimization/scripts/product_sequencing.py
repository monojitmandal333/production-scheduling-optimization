import pyomo.environ as pyo
import numpy as np
import pandas as pd
import os
import pickle
import datetime as dt

# data_location = "Input/F23_AL_Chewy.xlsx"
data_location = "Input/CO_Optimization.xlsx"
df_cot = pd.read_excel(data_location, sheet_name = "CO_Matrix")
# df_cot.columns = [f"product_{col}" if col != "from" else col for col in df_cot.columns]
# df_cot = pd.wide_to_long(
#     df_cot,stubnames="product_", i= "from", j="to_material_cd").reset_index().rename(columns = {"product_":"co_time"})
# df_cot = df_cot.rename(columns={"to_material_cd":"to"})

unique_products = df_cot["from"].unique()
from_product_list, to_product_list, co_time_list = [], [], []
for from_product in unique_products:
    for to_product in unique_products:
        from_product_list.append(from_product)
        to_product_list.append(to_product)
        co_time_list.append(df_cot[df_cot["from"] == from_product][to_product].values[0])
df_cot = pd.DataFrame({
    "from": from_product_list, 
    "to": to_product_list,
    "co_time": co_time_list})


model = pyo.ConcreteModel()
model.n_products = len(df_cot["from"].unique())

# Ranges
model.P = pyo.Set(initialize = df_cot["from"].unique())
model.Q = pyo.Set(initialize = df_cot["from"].unique()[1:])

# Data
COT_data = {
    (p,q):df_cot[(df_cot["from"] == p) & (df_cot["to"] == q)]["co_time"].to_numpy()[0] 
    for p in model.P for q in model.P
}

# Parameters
model.COT_pq = pyo.Param(model.P, model.P,initialize = COT_data)

# Decision Variables
model.x_pq = pyo.Var(model.P,model.P, domain = pyo.Binary)
model.u_p = pyo.Var(model.P, domain = pyo.PositiveIntegers)


def constraint_1(model,p):
    lhs = pyo.quicksum(model.x_pq[i,p] for i in model.P)
    rhs = 1
    return lhs == rhs
model.c_1 = pyo.Constraint(model.P, rule=constraint_1)

def constraint_2(model,p):
    lhs = pyo.quicksum(model.x_pq[p,j] for j in model.P)
    rhs = 1
    return lhs == rhs
model.c_2 = pyo.Constraint(model.P,rule = constraint_2)

def constraint_3(model,p,q):
    lhs = model.u_p[p] - model.u_p[q] + model.n_products*model.x_pq[p,q]
    rhs = model.n_products - 1
    return lhs <= rhs
model.c = pyo.Constraint(model.Q,model.Q,rule = constraint_3)


obj_expr = pyo.quicksum(model.COT_pq[p,q]*model.x_pq[p,q] for p in model.P for q in model.P)

model.obj = pyo.Objective(expr=obj_expr,sense=pyo.minimize)

model.write("models/CO_Optimization.lp",io_options={'symbolic_solver_labels': True})

# solver = pyo.SolverFactory('gurobi')
solver = pyo.SolverFactory('cbc',executable=r'.\CoinAll-1.6.0-win64-intel11.1\CoinAll-1.6.0-win64-intel11.1\cbc.exe')
# solver.options['MIPGap'] = 0.1
solver.options['TimeLimit'] = 100
result = solver.solve(model, tee=True)



# model = pickle.load(open("model_20230428185136.sav","rb"))

from_to_product_list = []
for from_to_product in model.x_pq:
    if model.x_pq[from_to_product].value == 1:
        from_to_product_list.append(from_to_product)
from_to_product_list

def find_next_product(current_product,from_to_product_list):
    for from_to_product in from_to_product_list:
        if from_to_product[0] == current_product:
            return from_to_product[1]


start_product = from_to_product_list[0][0]
next_product = None
current_product = start_product
product_sequence = [start_product]
while start_product != next_product:
    next_product = find_next_product(current_product,from_to_product_list)
    product_sequence.append(next_product)
    current_product = next_product
print(product_sequence)


p_list,q_list,x_list,co_time_list = [], [], [], []
for i in model.x_pq:
    p_list.append(i[0])
    q_list.append(i[1])
    x_list.append(model.x_pq[i[0],i[1]].value)
    co_time_list.append(model.COT_pq[i[0],i[1]])
df_X = pd.DataFrame({
    "from_material_cd":p_list,
    "to_material_cd":q_list,
    "X":x_list,
    "CO Time (hr)":co_time_list
})

p_list,u_list = [],[]
for i in model.u_p:
    p_list.append(i)
    u_list.append(model.u_p[i].value)
df_U = pd.DataFrame({
    "material_cd":p_list,
    "U":u_list
})

with pd.ExcelWriter(f"Output/Chewy_CO_Optimization.xlsx") as writer:
    df_X.to_excel(writer, sheet_name='optimal_solution')

for i in model.u_p:
    print(i,model.u_p[i].value)