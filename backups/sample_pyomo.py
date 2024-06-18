try:
    model
except NameError:
    pass
else:
    del(model)
model = pe.ConcreteModel()

P=pincodes
D=dcs
edges=set(dctdps.keys())
model.p = pe.Set(initialize=P)
model.d = pe.Set(initialize=D)
model.edges=pe.Set(within=model.p*model.d,initialize=edges)


model.dps=pe.Param(model.edges,initialize=dct_dps)
model.demand=pe.Param(model.p,initialize=dct_pin_demand)
model.cap=pe.Param(model.d,initialize=cap)

model.x=pe.Var(model.edges,within=pe.Binary)
model.dcload=pe.Var(model.d,within=pe.NonNegativeReals)
model.u0=pe.Var(within=pe.NonNegativeReals)

def assignment(model,p):
    lhs=pe.quicksum(model.x[p,d] for d in model.d)
    rhs=1
    return lhs==rhs

model.c1=pe.Constraint(model.p,rule=assignment)

def calc_load(model,d):
    lhs=pe.quicksum(model.x[p,d] * model.demand[p] for p in model.p)
    rhs=model.dcload[d]
    return lhs==rhs
model.c2=pe.Constraint(model.d, rule=calc_load)

model.c3 = pe.ConstraintList()

for d1, d2 in itertools.combinations(model.d, 2):
    lhs1=(model.dcload[d1]-model.dcload[d2])
    lhs2=(model.dcload[d2]-model.dcload[d1])
    rhs=model.u0
    model.c3.add(lhs1<=rhs)
    model.c3.add(lhs2<=rhs)

def cap_bound(model,d):
    lhs=model.dcload[d]
    rhs=model.cap[d]
    return lhs<=rhs
model.c4=pe.Constraint(model.d, rule=cap_bound)

obj_expr= model.u0+pe.quicksum(model.x[p,d]*model.dps[p,d] for p in model.p for d in model.d)
model.obj=pe.Objective(expr=obj_expr,sense=pe.minimize)

model.write('pin_dic_model.lp', io_options={'symbolic_solver_labels': True})

solver = po.SolverFactory('cbc',executable=r'D:\CoinAll-1.6.0-win64-intel11.1\CoinAll-1.6.0-win64-intel11.1\bin\cbc.exe')
result = solver.solve(model, tee=True)

model.solutions.load_from(result)

out_cols={'x':['pincode','dc','alloted']}

out = {}
# data_sol=pd.DataFrame()
for v in model.component_objects(pe.Var, active=True):
    if str(v) in out_cols.keys():
        df = pd.Series(v.get_values())
        df = df.reset_index()
        # print(df)
        # data_sol[str(v)]=df
        # break
        df.columns = out_cols[str(v)]
        out[str(v)] = df

final_df=out['x']

final_df=final_df.loc[final_df['alloted']==1.0]



