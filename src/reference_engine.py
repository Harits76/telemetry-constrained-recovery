"""Standalone replay of the 288 optima and 2016 frozen-policy scores.
Optional --rebuild-flows recomputes all1451040 integer terminal maximum flows.
This script has no imports from the earlier private study tree or network calls.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal,localcontext
import argparse,csv,gzip,json,hashlib,itertools,time
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow
ROOT=Path(__file__).resolve().parent

def rows(path):
 opener=gzip.open if str(path).endswith('.gz') else open
 with opener(path,'rt',newline='') as f:return list(csv.DictReader(f))
def masks(m=20,k=6):return np.array(sorted(sum(1<<i for i in c) for j in range(k+1) for c in itertools.combinations(range(m),j)),np.int64)
def arrivals(M,h,s):
 ready=np.full(len(M),s['backhaul']/2);nxt=ready.copy()
 for i,hi in enumerate(h):
  use=(M&(1<<i))!=0;start=np.maximum(nxt,ready);end=start+s['downlink']+s['turnaround']+hi;ready=np.where(use,end,ready);nxt=np.where(use,start+s['downlink']/s['duty'],nxt)
 return np.where(M==0,0,ready+s['backhaul']/2)
def transform(V,M,q):
 pos=np.full(1<<20,-1,np.int32);pos[M]=np.arange(len(M));out=V.astype(float).copy()
 for i in range(20):
  at=np.flatnonzero(M&(1<<i));parent=pos[M[at]^(1<<i)];assert (parent>=0).all();out[at]=(1-q[i])*out[parent]+q[i]*out[at]
 return out
def down(x):return np.maximum(0.,np.nextafter(x,-np.inf))
def up(x):return np.nextafter(x,np.inf)
def enclose(V,M,theta,p):
 pos=np.full(1<<20,-1,np.int32);pos[M]=np.arange(len(M));lo=V.astype(float).copy();hi=lo.copy();ql=down(down(theta)*down(p));qu=np.minimum(1.,up(up(theta)*up(p)))
 for i in range(20):
  a=np.flatnonzero(M&(1<<i));parent=pos[M[a]^(1<<i)];cl=down(1.-qu[i]);cu=up(1.-ql[i]);lo[a]=down(down(cl*lo[parent])+down(ql[i]*lo[a]));hi[a]=up(up(cu*hi[parent])+up(qu[i]*hi[a]))
 return lo,hi
def flow(case,mask):
 c=np.asarray(case['lower'],np.int64).copy();U=np.asarray(case['upper'],np.int64);arcs=np.asarray(case['resource_arcs']);bits=(mask>>np.arange(20))&1;c[arcs[bits.astype(bool)]]=U[arcs[bits.astype(bool)]]
 graph=csr_matrix((c,(case['tail'],case['head'])),shape=(case['n'],case['n']))
 return int(maximum_flow(graph,case['source'],case['sink'],method='dinic').flow_value)
def decimal_witness(mask,V,M,C,R):
 pos={int(x):i for i,x in enumerate(M)};ids=[i for i in range(20) if mask>>i&1]
 with localcontext() as ctx:
  ctx.prec=70;answer=Decimal(0)
  for cap in C:
   for rx in R:
    q=[Decimal(str(cap['probability'][i]))*Decimal(str(rx['probability'][i])) for i in ids];total=Decimal(0)
    for local in range(1<<len(ids)):
     chosen=sum(1<<ids[i] for i in range(len(ids)) if local>>i&1);prob=Decimal(1)
     for i,x in enumerate(q):prob*=x if local>>i&1 else 1-x
     total+=Decimal(int(V[pos[chosen]]))*prob
    answer+=Decimal(str(cap['weight']))*Decimal(str(rx['weight']))*total
  return answer

