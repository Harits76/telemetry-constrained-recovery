"""Replay the earlier seven-rule follow-up and reception transport check."""
from pathlib import Path
import gzip,json
import numpy as np
from reference_engine import arrivals
from supporting import objective
from policies import cut_membership,select_all
from run_study import write,choose
ROOT=Path(__file__).resolve().parents[1]
with gzip.open(ROOT/'data/historical_transport_cases.json.gz','rt') as f:cases=json.load(f)
tabs=np.load(ROOT/'data/historical_transport_tables.npz');M=tabs['masks'];pos=np.full(1<<20,-1,int);pos[M]=np.arange(len(M));bits=(M[:,None]>>np.arange(20))&1
rows=[];opt=[]
for case in cases:
    name=f"{case['family']}_{case['seed']}";V=tabs[name]
    h=np.array(case['reply_airtimes']);cost=bits@(case['service']['downlink']+h);time=arrivals(M,h,case['service']);cut=cut_membership(case)
    for prior,C in case['capacity'].items():
        for reception,R in case['reception'].items():
            J=objective(V,M,C,R)
            for B in [.42,.7]:
                valid=(cost<=B+1e-12)&(time<=3+1e-12);at=choose(J,valid,M,cost);best=float(J[at])
                meta=dict(Cohort=case['cohort'],Family=case['family'],Seed=case['seed'],Prior=prior,Reception=reception,Budget=B)
                opt.append(dict(meta,Optimum=best,OptimalMask=int(M[at])))
                choices=select_all(case,M,V,J,cost,valid,prior,reception,B,cut)
                for policy,mask in choices.items():rows.append(dict(meta,Policy=policy,Mask=mask,ExpectedFlow=float(J[pos[mask]]),ExactGap=max(0.,best-float(J[pos[mask]]))))
write(ROOT/'results/Historical_Transport_Policies.csv',rows);write(ROOT/'results/Historical_Transport_Optima.csv',opt)
print(f'Replayed {len(rows)} historical policy scores and {len(opt)} optima')
