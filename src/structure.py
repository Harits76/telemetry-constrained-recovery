"""Budget-restricted exact cut and singleton residual diagnostics."""
from pathlib import Path
import csv,json
import numpy as np
from policies import cut_membership
from reference_engine import arrivals
from run_study import write
ROOT=Path(__file__).resolve().parents[1]
rows=[]
for path in sorted((ROOT/'cases').glob('*/*.json')):
    c=json.loads(path.read_text());tab=np.load(ROOT/f'results/{path.stem}_terminal.npz');M=tab['masks'];V=tab['values'];bits=(M[:,None]>>np.arange(20))&1
    pos=np.full(1<<20,-1,int);pos[M]=np.arange(len(M));a=V[pos[1<<np.arange(20)]]-V[0]
    cut=cut_membership(c);arcs=np.array(c['resource_arcs']);width=(np.array(c['upper'])-np.array(c['lower']))[arcs]*cut[arcs]
    residual=np.abs(V-V[0]-bits@a);cut_residual=V[0]+bits@width-V
    h=np.array(c['reply_airtimes']);cost=bits@(.046336+h);time=arrivals(M,h,c['service'])
    for B in [.28,.42,.7]:
        valid=(cost<=B+1e-12)&(time<=3+1e-12);epsilon=int(residual[valid].max());cutgap=int(cut_residual[valid].max())
        assert cutgap>=0
        rows.append(dict(Cohort=c['cohort'],Family=c['family'],Seed=c['seed'],Budget=B,Epsilon=epsilon,BudgetCutRegret=cutgap,Additive=int(epsilon==0),CutPersistent=int(cutgap==0)))
write(ROOT/'results/Restricted_Structure.csv',rows)
lookup={(r['Family'],str(r['Seed']),r['Budget']):r['Epsilon'] for r in rows}
for r in csv.DictReader((ROOT/'results/all_Policies.csv').open()):
    if r['Policy']=='MODULAR_DP':assert float(r['ExactGap'])<=2*lookup[r['Family'],r['Seed'],float(r['Budget'])]+1e-8
for cohort in ['old','test']:
    n=sum(r['Additive']*6 for r in rows if r['Cohort']==cohort and r['Budget'] in [.42,.7])
    print(f'{cohort}: zero residual certifies {n}/288 main conditions')
