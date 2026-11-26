"""Standalone replay of width, prior-error and order analyses in the paper."""
from pathlib import Path
import argparse,csv,gzip,itertools,json
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow
from information import criterion_tables,observation_groups
from reference_engine import arrivals
from policies import seed
from run_study import write
ROOT=Path(__file__).resolve().parents[1]

def transform(values,M,q):
    out=np.array(values,float).copy();pos=np.full(1<<len(q),-1,int);pos[M]=np.arange(len(M))
    for i,p in enumerate(q):
        at=np.flatnonzero(M&(1<<i));parent=pos[M[at]^(1<<i)]
        out[at]=(1-p)*out[parent]+p*out[at]
    return out

def objective(V,M,C,R):
    return sum(c['weight']*r['weight']*transform(V,M,np.array(c['probability'])*np.array(r['probability'])) for c in C for r in R)

def choose(J,valid,cost,M):
    a=np.flatnonzero(valid);tie=a[np.isclose(J[a],J[a].max(),rtol=0,atol=1e-9)]
    return int(tie[np.lexsort((M[tie],cost[tie]))[0]])

def altered(name,C,R):
    if name=='MATCHED':return C,R
    def collapse(A):return [dict(weight=1.,probability=sum(a['weight']*np.array(a['probability']) for a in A).tolist())]
    if name=='MARGINAL_ONLY':return collapse(C),collapse(R)
    def adjust(p):
        p=np.array(p)
        return .5+.5*(p-.5) if name=='SHRUNK' else np.clip(p+(.2 if name=='SHIFT_UP' else -.2),.05,.95)
    return [dict(weight=c['weight'],probability=adjust(c['probability']).tolist()) for c in C],R

def solve(case,caps):
    graph=csr_matrix((np.asarray(caps,np.int64),(case['tail'],case['head'])),shape=(case['n'],case['n']))
    result=maximum_flow(graph,case['source'],case['sink'],method='dinic')
    residual=(graph-result.flow).tocsr();seen={case['source']};todo=list(seen)
    while todo:
        u=todo.pop()
        for j in range(residual.indptr[u],residual.indptr[u+1]):
            v=int(residual.indices[j])
            if residual.data[j]>0 and v not in seen:seen.add(v);todo.append(v)
    cut=np.array([u in seen and v not in seen for u,v in zip(case['tail'],case['head'])])
    assert np.asarray(caps)[cut].sum()==result.flow_value
    return int(result.flow_value),cut

def width_rows(case):
    lo=np.array(case['lower']);up=np.array(case['upper']);arcs=np.array(case['resource_arcs']);base,cut=solve(case,lo);rows=[]
    for alpha in [.05,.1,.25,.5,1.]:
        upper=lo+np.floor(alpha*(up-lo)).astype(int);corner=np.where(cut,upper,lo)
        f,_=solve(case,corner);regret=int(upper[cut].sum()-f);assert regret>=0
        width=int((upper-lo)[cut].sum())
        rows.append(dict(Family=case['family'],Seed=case['seed'],Candidates=len(arcs),Placement=case.get('placement','ALL20'),WidthFraction=alpha,Persistent=int(regret==0),CutWidth=width,NontrivialCertificate=int(regret==0 and width>0),FullCutRegret=regret))
    return rows

def prior_rows(case,V,M,reduced):
    m=len(case['resource_arcs']);bits=(M[:,None]>>np.arange(m))&1;h=np.array(case['reply_airtimes']);s=case['service']
    native=s['downlink']+h;cost=bits@native;arrival=arrivals(M,h,s)
    arcs=np.array(case['resource_arcs']);width=np.array(case['upper'])[arcs]-np.array(case['lower'])[arcs];_,cut=solve(case,np.array(case['lower']));member=cut[arcs]
    rows=[];groups=observation_groups(m,m) if reduced else None
    meta=dict(Family=case['family'],Seed=case['seed'],Placement=case.get('placement','ALL20'))
    for prior,C in case['capacity'].items():
        for reception,R in case['reception'].items():
            trueJ=objective(V,M,C,R)
            for assumption in ['MATCHED','SHRUNK','SHIFT_UP','SHIFT_DOWN','MARGINAL_ONLY']:
                ac,ar=altered(assumption,C,R);J=objective(V,M,ac,ar)
                if reduced:
                    gain,_=criterion_tables(case,V,M,groups,ac)
                    FM=sum(r['weight']*transform(gain,M,np.array(r['probability'])) for r in ar)
                    mx=sum(c['weight']*np.array(c['probability']) for c in ac);mr=sum(r['weight']*np.array(r['probability']) for r in ar)
                    order=np.lexsort((np.arange(m),-width*mx*mr/native,-member.astype(int)))
                for B in [.42,.7]:
                    valid=(cost<=B+1e-12)&(arrival<=3+1e-12)
                    choices={'EXACT_BELIEF':int(M[choose(J,valid,cost,M)])}
                    if reduced:
                        choices['FLOW_MSE']=int(M[choose(FM,valid,cost,M)])
                        mask=0
                        while True:
                            cand=[mask|(1<<i) for i in range(m) if not mask>>i&1 and valid[mask|(1<<i)]]
                            if not cand:break
                            scores=[(J[a]-J[mask])/(cost[a]-cost[mask]) for a in cand];j=int(np.argmax(scores))
                            if scores[j]<=1e-10:break
                            mask=cand[j]
                        choices['GREEDY_FLOW']=mask;mask=0
                        for i in order:
                            if valid[mask|(1<<int(i))]:mask|=1<<int(i)
                        choices['CUT']=mask
                    pos=np.full(1<<m,-1,int);pos[M]=np.arange(len(M))
                    for policy,mask in choices.items():
                        value=float(trueJ[pos[mask]]);best=float(trueJ[valid].max())
                        rows.append(dict(meta,TruePrior=prior,TrueReception=reception,Assumption=assumption,Budget=B,Policy=policy,Mask=mask,TrueExpectedFlow=value,TrueOptimalFlow=best,TrueRegret=max(0.,best-value)))
    return rows

def order_rows(case,V):
    m=8;M=np.arange(256);h=np.array(case['reply_airtimes']);cost=((M[:,None]>>np.arange(m))&1)@(.046336+h)
    orders={'ID':np.arange(m),'SHORT_LAST':np.lexsort((np.arange(m),-h)),'LONG_LAST':np.lexsort((np.arange(m),h)),'RANDOM':np.random.default_rng(seed('service-order-check',case['family'],case['seed'])).permutation(m)}
    times={}
    for name,order in orders.items():
        ready=np.full(256,.025);nxt=ready.copy()
        for i in order:
            start=np.maximum(ready,nxt);use=(M&(1<<int(i)))!=0
            ready=np.where(use,start+.046336+.01+h[i],ready);nxt=np.where(use,start+.46336,nxt)
        times[name]=np.where(M==0,0,ready+.025)
    rows=[]
    for prior,C in case['capacity'].items():
        for reception,R in case['reception'].items():
            J=objective(V,M,C,R)
            for B,H in itertools.product([.42,.7],[.60,.63,.66,1.08,1.095,1.12,3.]):
                base=float(J[(cost<=B+1e-12)&(times['ID']<=H+1e-12)].max())
                for name,time in times.items():
                    valid=(cost<=B+1e-12)&(time<=H+1e-12);at=choose(J,valid,cost,M)
                    rows.append(dict(Family=case['family'],Seed=case['seed'],Prior=prior,Reception=reception,Budget=B,Horizon=H,Order=name,OptimalMask=int(M[at]),OptimalFlow=float(J[at]),IDOptimalFlow=base,OrderDelta=float(J[at]-base)))
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rebuild-reduced',action='store_true');a=p.parse_args()
    with gzip.open(ROOT/'data/reduced_cases.json.gz','rt') as f:cases=json.load(f)
    width=[];priors=[];orders=[]
    for j,case in enumerate(cases):
        V=np.array(case['values']);M=np.arange(256)
        if a.rebuild_reduced:
            for mask in M:
                caps=np.array(case['lower']);arcs=np.array(case['resource_arcs']);on=(mask>>np.arange(8))&1
                caps[arcs[on.astype(bool)]]=np.array(case['upper'])[arcs[on.astype(bool)]]
                assert solve(case,caps)[0]==V[mask]
        width+=width_rows(case);priors+=prior_rows(case,V,M,True)
        if case['placement']=='BALANCED':orders+=order_rows(case,V)
        if (j+1)%48==0:print(f'Reduced cases {j+1}/288',flush=True)
    for name,rows in [('Supporting_Prior8',priors),('Supporting_Order8',orders)]:
        write(ROOT/'results'/f'{name}.csv',rows)
    prior20=[]
    for path in sorted((ROOT/'cases/original').glob('*.json')):
        case=json.loads(path.read_text());tab=np.load(ROOT/f'results/{path.stem}_terminal.npz')
        width+=width_rows(case);prior20+=prior_rows(case,tab['values'],tab['masks'],False)
    write(ROOT/'results/Supporting_Width.csv',width);write(ROOT/'results/Supporting_Prior20.csv',prior20)
    print(f'PASS: {len(priors)} prior8, {len(orders)} order8, {len(prior20)} prior20 rows')
