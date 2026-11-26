"""Standalone full-scale allocation/estimation-objective comparison."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import argparse, csv, hashlib, json, subprocess, time
import numpy as np
from information import criterion_tables, observation_groups
from reference_engine import masks, transform, arrivals, enclose, down, up
from policies import cut_membership, select_all
ROOT = Path(__file__).resolve().parents[1]

def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def choose(score, valid, M, cost):
    at=np.flatnonzero(valid); best=score[at].max()
    tied=at[np.isclose(score[at],best,rtol=0,atol=1e-10)]
    return int(tied[np.lexsort((M[tied],cost[tied]))[0]])

def run(path):
    started=time.perf_counter(); case=json.loads(Path(path).read_text()); name=Path(path).stem
    work=ROOT/'work'; work.mkdir(exist_ok=True)
    graph=work/f'{name}.txt'; dest=work/f'{name}.bin'
    bit={a:i for i,a in enumerate(case['resource_arcs'])}
    lines=[f"{case['n']} {len(case['tail'])} {case['source']} {case['sink']} 20"]
    lines += [f'{u} {v} {l} {h} {bit.get(j,-1)}' for j,(u,v,l,h) in enumerate(zip(case['tail'],case['head'],case['lower'],case['upper']))]
    graph.write_text('\n'.join(lines)+'\n')
    if not dest.exists(): subprocess.run([str(work/'full_truth'),str(graph),str(dest)],check=True,stdout=subprocess.DEVNULL)
    full=np.fromfile(dest,dtype=np.int32); assert len(full)==1<<20
    M=masks(); V=full[M]; pos=np.full(1<<20,-1,int);pos[M]=np.arange(len(M))
    groups=observation_groups(20,6)
    bits=(M[:,None]>>np.arange(20))&1
    s=case['service']; cost=bits@(s['downlink']+np.array(case['reply_airtimes']))
    arrival=arrivals(M,np.array(case['reply_airtimes']),s)
    cut=cut_membership(case); policy_rows=[]; opt_rows=[]; criterion_rows=[]
    for prior,C in case['capacity'].items():
        flow_g,summary_g=criterion_tables(case,full,M,groups,C)
        for reception,R in case['reception'].items():
            J=np.zeros(len(M)); low=J.copy(); high=J.copy()
            for c in C:
                for r in R:
                    theta=np.array(c['probability']);p=np.array(r['probability']);w=c['weight']*r['weight']
                    J+=w*transform(V,M,theta*p)
                    L,U=enclose(V,M,theta,p)
                    low=down(low+down(down(down(c['weight'])*down(r['weight']))*L))
                    high=up(high+up(up(up(c['weight'])*up(r['weight']))*U))
            criteria=[sum(r['weight']*transform(g,M,np.array(r['probability'])) for r in R) for g in [flow_g,summary_g]]
            for budget in [.28,.42,.70]:
                valid=(cost<=budget+1e-12)&(arrival<=s['horizon']+1e-12)
                j=choose(J,valid,M,cost); optimum=float(J[j]);gap=float(high[valid].max()-low[j]);assert 0<=gap<1e-8
                meta=dict(Cohort=case['cohort'],Family=case['family'],Seed=case['seed'],Prior=prior,Reception=reception,Budget=budget)
                opt_rows.append(dict(meta,OptimalMask=int(M[j]),Optimum=optimum,InitialFlow=int(V[0]),Lower=float(low[j]),Upper=float(high[valid].max()),NumericalGap=gap,FeasibleSubsets=int(valid.sum())))
                choices=select_all(case,M,V,J,cost,valid,prior,reception,budget,cut)
                for label,criterion in zip(['FLOW_MSE','SUMMARY_VOI'],criteria):
                    at=choose(criterion,valid,M,cost);choices[label]=int(M[at])
                    criterion_rows.append(dict(meta,Policy=label,Mask=int(M[at]),VarianceReduction=float(criterion[at])))
                for label,mask in choices.items():
                    at=pos[mask];assert valid[at]
                    policy_rows.append(dict(meta,Policy=label,Mask=mask,ExpectedFlow=float(J[at]),ExactGap=max(0.,optimum-float(J[at])),Attempts=mask.bit_count(),Reservation=float(cost[at])))
    np.savez_compressed(ROOT/'results'/f'{name}_terminal.npz',masks=M,values=V)
    record=dict(Case=name,States=len(full),TruthSHA256=hashlib.sha256(dest.read_bytes()).hexdigest(),Seconds=time.perf_counter()-started)
    print(f'{name}: full truth + nine rules complete ({record["Seconds"]:.1f}s)',flush=True)
    return opt_rows,policy_rows,criterion_rows,record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=2);p.add_argument('--cohort',choices=['original','test','all'],default='all');a=p.parse_args()
    (ROOT/'results').mkdir(exist_ok=True);(ROOT/'work').mkdir(exist_ok=True)
    subprocess.run(['g++','-std=c++17','-O3',str(ROOT/'src/full_truth.cpp'),'-o',str(ROOT/'work/full_truth')],check=True)
    paths=sorted((ROOT/'cases').glob(('*' if a.cohort=='all' else a.cohort)+'/*.json'))
    start=time.perf_counter();opt=[];pol=[];crit=[];audit=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for o,s,c,r in pool.map(run,paths):
            opt+=o;pol+=s;crit+=c;audit.append(r)
            # Checkpoints survive an interrupted long run.
            for name,rows in [('Optima',opt),('Policies',pol),('Information_Criteria',crit),('Truth_Audit',audit)]:write(ROOT/'results'/f'{a.cohort}_{name}.csv',rows)
    (ROOT/'results'/f'{a.cohort}_Run.json').write_text(json.dumps(dict(Cases=len(paths),States=len(paths)*(1<<20),PolicyRows=len(pol),WallSeconds=time.perf_counter()-start),indent=2)+'\n')
