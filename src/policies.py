"""Table-backed execution of the seven existing rules; no fitted parameters."""
import hashlib, math
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

POLICIES = ['CUT','RANDOM','MYOPIC_FLOW','LAZY_GREEDY','LOCAL_SWAP','MODULAR_DP','CUT_DP']
def seed(*parts):
    return int(hashlib.sha256('|'.join(map(str, ('pi-shared-flow-1',)+parts)).encode()).hexdigest()[:16],16)

def cut_membership(case):
    c = np.asarray(case['lower'],np.int64)
    graph = csr_matrix((c,(case['tail'],case['head'])), shape=(case['n'],case['n']))
    r = maximum_flow(graph,case['source'],case['sink'],method='dinic')
    residual = (graph-r.flow).tocsr(); seen={case['source']}; todo=list(seen)
    while todo:
        u=todo.pop()
        for j in range(residual.indptr[u],residual.indptr[u+1]):
            v=int(residual.indices[j])
            if residual.data[j]>0 and v not in seen:
                seen.add(v);todo.append(v)
    cut=np.array([u in seen and v not in seen for u,v in zip(case['tail'],case['head'])])
    assert c[cut].sum()==r.flow_value
    return cut

def knapsack(gain,cost,budget):
    us=np.rint(np.asarray(cost)*1e6).astype(int);unit=math.gcd(*map(int,us));weights=us//unit
    C=int(math.floor((budget*1e6+1e-6)/unit));dp=np.full(C+1,-np.inf);dp[0]=0.;chosen=np.zeros(C+1,np.int64)
    for i,w in enumerate(weights):
        old=dp.copy();om=chosen.copy();cand=old[:-w]+gain[i];cm=om[:-w]|(1<<i)
        finite=np.isfinite(cand)&np.isfinite(old[w:]);equal=np.zeros(len(cand),bool)
        equal[finite]=np.abs(cand[finite]-old[w:][finite])<1e-10
        use=(cand>old[w:]+1e-10)|(equal&(cm<om[w:]))
        dp[w:]=np.where(use,cand,old[w:]);chosen[w:]=np.where(use,cm,om[w:])
    best=np.nanmax(dp);at=np.flatnonzero(np.isclose(dp,best,rtol=0,atol=1e-9))
    j=at[np.lexsort((chosen[at],at))[0]]
    return int(chosen[j])

def select_all(case,M,V,J,cost,valid,prior,reception,budget,cut):
    pos=np.full(1<<20,-1,int);pos[M]=np.arange(len(M));m=20
    native=case['service']['downlink']+np.asarray(case['reply_airtimes'])
    arcs=np.asarray(case['resource_arcs']);width=np.asarray(case['upper'])[arcs]-np.asarray(case['lower'])[arcs]
    member=cut[arcs]
    mx=sum(c['weight']*np.asarray(c['probability']) for c in case['capacity'][prior])
    mr=sum(c['weight']*np.asarray(c['probability']) for c in case['reception'][reception])
    q=mx*mr
    def score(mask):
        assert pos[mask]>=0
        return float(J[pos[mask]])
    def feasible(mask):
        return pos[mask]>=0 and bool(valid[pos[mask]])
    answers={}
    for policy in ['CUT','RANDOM','MYOPIC_FLOW']:
        if policy=='CUT':order=np.lexsort((np.arange(m),-width*q/native,-member.astype(int)))
        elif policy=='RANDOM':order=np.random.default_rng(seed('large-random',case['family'],case['seed'])).permutation(m)
        else:order=np.lexsort((np.arange(m),-(J[pos[1<<np.arange(m)]]-J[0])/native))
        mask=0
        for i in order:
            a=mask|(1<<int(i))
            if feasible(a):mask=a
        answers[policy]=mask
    mask=0
    while True:
        candidates=[mask|(1<<i) for i in range(m) if not mask>>i&1 and feasible(mask|(1<<i))]
        if not candidates:break
        values=[(score(a)-score(mask))/sum(native[i] for i in range(m) if (a^mask)>>i&1) for a in candidates]
        j=int(np.argmax(values))
        if values[j]<=1e-10:break
        mask=candidates[j]
    answers['LAZY_GREEDY']=mask
    for sweep in range(2):
        candidates=sorted({(mask^(1<<i))|(1<<j) for i in range(m) if mask>>i&1 for j in range(m) if not mask>>j&1 and feasible((mask^(1<<i))|(1<<j))})
        best=max(candidates,key=score,default=mask)
        if score(best)<=score(mask)+1e-10:break
        mask=best
    answers['LOCAL_SWAP']=mask
    singleton=V[pos[1<<np.arange(m)]]-V[0]
    answers['MODULAR_DP']=knapsack(singleton*q,native,budget)
    answers['CUT_DP']=knapsack(width*member*q,native,budget)
    assert all(feasible(mask) for mask in answers.values())
    return answers
