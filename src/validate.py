"""Independent full-state posterior, flow and decimal-witness checks."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
import csv,json
import numpy as np
from information import criterion_tables
from reference_engine import decimal_witness
from supporting import solve
from run_study import write
ROOT=Path(__file__).resolve().parents[1]

def check_case(path):
    case=json.loads(Path(path).read_text());name=Path(path).stem
    full=np.fromfile(ROOT/f'work/{name}.bin',dtype=np.int32)
    states=np.arange(1<<20);arcs=np.array(case['resource_arcs'])
    probes=np.array([0,1,63,sum(1<<i for i in [0,3,7,12,16,19])])
    groups=[]
    for R in probes:
        ids=np.array([i for i in range(20) if R>>i&1],int).reshape(1,-1)
        local=(np.arange(1<<ids.shape[1])[:,None]>>np.arange(ids.shape[1]))&1
        sub=np.sum(local[None,:,:]*(1<<ids[:,None,:]),axis=2,dtype=np.int64)
        groups.append((ids,local,sub))
    lo=np.array(case['lower'])[arcs];delta=np.array(case['upper'])[arcs]-lo
    Z=np.full(len(states),lo.mean())
    for i in range(20):Z+=delta[i]/20*((states>>i)&1)
    rows=[]
    for prior,C in case['capacity'].items():
        got=criterion_tables(case,full,probes,groups,C)
        P=np.zeros(len(states))
        for c in C:
            p=np.full(len(states),c['weight'])
            for i,q in enumerate(c['probability']):p*=np.where((states>>i)&1,q,1-q)
            P+=p
        np.testing.assert_allclose(P.sum(),1,atol=1e-12)
        for label,values,G in zip(['Flow','MeanCapacity'],[full,Z],got):
            mu=P@values
            for j,R in enumerate(probes):
                ids=[i for i in range(20) if R>>i&1]
                code=sum(((states>>i)&1)<<k for k,i in enumerate(ids)) if ids else np.zeros(len(states),int)
                mass=np.bincount(code,weights=P,minlength=1<<len(ids))
                moment=np.bincount(code,weights=P*(values-mu),minlength=len(mass))
                exact=float(np.sum(moment**2/mass))
                assert np.isclose(G[j],exact,atol=1e-6,rtol=1e-10),(name,prior,label,int(R),G[j],exact)
                rows.append(dict(Case=name,Prior=prior,Target=label,ObservedMask=int(R),Transformed=float(G[j]),Literal=exact,AbsoluteError=abs(float(G[j])-exact)))
    for mask in [0,(1<<20)-1,int(np.random.default_rng(42).integers(1<<20))]:
        caps=np.array(case['lower']);on=((mask>>np.arange(20))&1).astype(bool)
        caps[arcs[on]]=np.array(case['upper'])[arcs[on]]
        assert solve(case,caps)[0]==full[mask]
    return rows

if __name__=='__main__':
    rows=[]
    paths=sorted((ROOT/'cases').glob('*/*.json'));assert len(paths)==48
    with ProcessPoolExecutor(max_workers=2) as pool:
        for i,r in enumerate(pool.map(check_case,paths),1):
            rows+=r
            if i%8==0:print(f'Full-state posterior and independent flow checks {i}/48',flush=True)
    write(ROOT/'results/Fullstate_Posterior_Checks.csv',rows)
    opt=list(csv.DictReader((ROOT/'results/all_Optima.csv').open()));witness=[]
    for path in paths:
        case=json.loads(path.read_text());tab=np.load(ROOT/f'results/{path.stem}_terminal.npz');M=tab['masks'];V=tab['values']
        for row in opt:
            if row['Family']!=case['family'] or int(row['Seed'])!=case['seed']:continue
            value=decimal_witness(int(row['OptimalMask']),V,M,case['capacity'][row['Prior']],case['reception'][row['Reception']])
            assert Decimal.from_float(float(row['Lower']))<=value<=Decimal.from_float(float(row['Upper']))
            witness.append(dict(Case=path.stem,Prior=row['Prior'],Reception=row['Reception'],Budget=row['Budget'],DecimalWitness=str(value)))
    assert len(witness)==864
    write(ROOT/'results/Decimal_Witnesses.csv',witness)
    record=dict(cases=48,fullstate_posterior_values=len(rows),maximum_posterior_absolute_error=max(r['AbsoluteError'] for r in rows),independent_dinic_flow_values=144,decimal_optimal_witnesses=864,maximum_allocation_numerical_gap=max(float(r['NumericalGap']) for r in opt))
    (ROOT/'results/Validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
