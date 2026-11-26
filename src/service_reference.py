"""Optimistic serial-service reference with correctly adapted batch eligibility.

This separates the cost of the service constraint itself from transporting
a batch chosen for the nominal service. Reception is perfect; it is not an
optimum over the physical MAC or interference process.
"""
from pathlib import Path
import json,itertools
import numpy as np
from reference_engine import transform,arrivals
from run_study import write,choose
from packet_experiment import FAMILIES
ROOT=Path(__file__).resolve().parents[1]
rows=[]
for family in FAMILIES:
    case=json.loads((ROOT/f'cases/original/{family}_6100.json').read_text())
    tab=np.load(ROOT/f'results/{family}_6100_terminal.npz');M=tab['masks'];V=tab['values']
    ideal=transform(V,M,np.full(20,.5));h=np.array(case['reply_airtimes'])
    cost=((M[:,None]>>np.arange(20))&1)@(case['service']['downlink']+h)
    for H,duty,budget in itertools.product([1.,3.,6.],[.01,.1],[.28,.42,.70]):
        service=dict(case['service'],horizon=H,duty=duty)
        arrival=arrivals(M,h,service);valid=(cost<=budget+1e-12)&(arrival<=H+1e-12)
        at=choose(ideal,valid,M,cost)
        rows.append(dict(Family=family,Seed=6100,Horizon=H,Duty=duty,Budget=budget,OptimalMask=int(M[at]),IdealServiceOptimum=float(ideal[at]),FeasibleBatches=int(valid.sum()),MaximumReports=max(int(M[j]).bit_count() for j in np.flatnonzero(valid))))
write(ROOT/'results/Service_Optima.csv',rows)
print(f'Computed {len(rows)} service-adapted exact references')
