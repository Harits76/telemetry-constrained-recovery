"""Regenerate the aggregate values used by the manuscript and figures."""
from pathlib import Path
import csv,collections
import numpy as np
from run_study import write
ROOT=Path(__file__).resolve().parents[1]
a=list(csv.DictReader((ROOT/'results/all_Policies.csv').open()))
groups=collections.defaultdict(list)
for r in a:
    if float(r['Budget']) in [.42,.7]:groups[r['Cohort'],r['Policy']].append(r)
summary=[]
for (cohort,policy),rows in groups.items():
    gaps=[float(r['ExactGap']) for r in rows];assert len(rows)==288
    summary.append(dict(Cohort=cohort,Policy=policy,N=len(rows),MeanGap=np.mean(gaps),WorstGap=max(gaps),Exact=sum(v<1e-8 for v in gaps)))
write(ROOT/'results/Fullscale_Summary.csv',summary)
groups=collections.defaultdict(list)
for r in a:
    if r['Cohort']=='old' and float(r['Budget']) in [.42,.7]:groups[r['Prior'],r['Reception'],float(r['Budget']),r['Policy']].append(r)
summary=[]
for key,rows in groups.items():
    summary.append(dict(zip(['Prior','Reception','Budget','Policy'],key),N=len(rows),MeanFlow=np.mean([float(r['ExpectedFlow']) for r in rows]),MeanExactGap=np.mean([float(r['ExactGap']) for r in rows]),WorstExactGap=max(float(r['ExactGap']) for r in rows)))
write(ROOT/'results/Policy_Exact_Summary.csv',summary)
groups=collections.defaultdict(list)
for r in csv.DictReader((ROOT/'results/Supporting_Width.csv').open()):groups[int(r['Candidates']),float(r['WidthFraction'])].append(r)
summary=[]
for key,rows in groups.items():summary.append(dict(Candidates=key[0],WidthFraction=key[1],N=len(rows),NontrivialCertificates=sum(int(r['NontrivialCertificate']) for r in rows),AllCertificates=sum(int(r['Persistent']) for r in rows)))
write(ROOT/'results/Width_Summary.csv',summary)
print('Regenerated full-scale, heatmap and structural summaries')
