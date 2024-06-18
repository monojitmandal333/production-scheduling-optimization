"""
@author: Monojit Mandal (G666966)
"""
import random
import numpy as np
import docplex.mp.model as cpx
import pandas as pd
model = cpx.Model(name="sequencing_optimization")

# Define Sets------------------------------------------------------------------------------------------
n_timeframes = 20
n_products = 4

T = range(n_timeframes)
P = range(n_products)

# Define parameters---------------------------------------------------------------------------------------
df_cot = np.array(pd.read_excel("data.xlsx", sheet_name = "CO").set_index("From"))
df_dos = np.array(pd.read_excel("data.xlsx", sheet_name = "DOS").set_index("product_name"))
df_idos = np.array(pd.read_excel("data.xlsx", sheet_name = "IDOS").set_index("product_name"))
df_demand = np.array(pd.read_excel("data.xlsx", sheet_name = "demand").set_index("product_name"))
df_lr = np.array(pd.read_excel("data.xlsx", sheet_name = "line_rate").set_index("product_name"))

COT_pq = {(p,q):df_cot[p][q] for p in P for q in P}
DOS_pt = {(p,t):df_dos[p][0] for p in P for t in T}
IDOS_p = {p:df_idos[p][0] for p in P}
OR_p = {p:df_demand[p][0]/365 for p in P}
LR_p = {p:df_lr[p][0] for p in P}

# Define decision variables--------------------------------------------------------------------------------
X_pt = {(p,t): model.binary_var(name="X_pt_{}_{}".format(p,t)) for p in P for t in T}
W_pqt = {(p,q,t): model.binary_var(name="W_pqt_{}_{}_{}".format(p,q,t)) for p in P for q in P for t in T}

# Objective function---------------------------------------------------------------------------------
objective = model.sum(COT_pq[(p,q)]*W_pqt[p,q,t] for p in P for q in P for t in T[:len(T)-1])

# Constraints----------------------------------------------------------------------------------------

# Linear conversion constraint 1.a
contraint_1a = {(p,q,t) : 
    model.add_constraint(ct=W_pqt[p,q,t] >= X_pt[p,t] + X_pt[q,t+1]-1,
                             ctname="contraint_1a_{}_{}_{}".format(p,q,t)) 
    for p in P for q in P for t in T[:len(T)-1]}

# Linear conversion constriant 1.b
contraint_1b = {(p,q,t) : 
    model.add_constraint(ct=W_pqt[p,q,t] <= X_pt[p,t],
                             ctname="contraint_1b_{}_{}_{}".format(p,q,t)) 
    for p in P for q in P for t in T}

# Linear conversion constriant 1.c
contraint_1c = {(p,q,t) : 
    model.add_constraint(ct=W_pqt[p,q,t] <= X_pt[q,t+1],
                             ctname="contraint_1c_{}_{}_{}".format(p,q,t)) 
    for p in P for q in P for t in T[:len(T)-1]}

# Only a product can run within a given period
contraint_2 = {t: 
    model.add_constraint(ct = model.sum(X_pt[p,t] for p in P) == 1,
                         ctname="contraint_2_{}".format(t))
    for t in T}

# # Days of Supply to be maintained
# constraint_3 = {
#     (t,p):model.add_constraint(
#         ct = model.sum(X_pt[p,i] for i in T[:t+1]) >= (DOS_pt[(p,t)] + t -IDOS_p[p])*OR_p[p]/LR_p[p],
#         ctname="Constraint_3_{}_{}".format(p,t)
#     )
#     for p in P for t in T
# }

constraint_3 = {
    (t,p):model.add_constraint(
        ct = model.sum(X_pt[p,t] for t in T) >= OR_p[p]*n_timeframes/LR_p[p],
        ctname="Constraint_3_{}".format(p)
    )
    for p in P
}

# Model objective-------------------------------------------------------------------------------------
model.minimize(objective)

# Solve Model-----------------------------------------------------------------------------------------
model.solve()
model.export_as_lp("cplex_mode.lp")
model.solve_details



df_X = pd.DataFrame(columns = T, index = P)
for p in P:
    for t in T:
        df_X.loc[p,t] = round(X_pt[p,t].solution_value)
print(df_X)
# print(objective.solution_value)