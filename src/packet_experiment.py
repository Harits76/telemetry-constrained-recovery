"""Prepare fixed paired ns-3 trials and evaluate their received reports."""
from pathlib import Path
import argparse,csv,hashlib,json,itertools,subprocess,time
import numpy as np
from run_study import write
ROOT=Path(__file__).resolve().parents[1]
FAMILIES=['anaheim','berlin','massachusetts','barcelona','ER64','GRID64']
def seed(*parts):return int(hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()[:8],16)

def prepare():
    dest=ROOT/'work/packets';dest.mkdir(parents=True,exist_ok=True)
    policies=list(csv.DictReader((ROOT/'results/all_Policies.csv').open()))
    rows=[];lines=[]
    for family in FAMILIES:
        case=json.loads((ROOT/f'cases/original/{family}_6100.json').read_text())
        longmask=sum(1<<i for i,h in enumerate(case['reply_airtimes']) if h>.06)
        choices=[p for p in policies if p['Family']==family and p['Seed']=='6100' and p['Prior']=='I05' and p['Reception']=='INDEP80']
        assert len(choices)==27, (family,len(choices))
        for H,duty,bg,radius in itertools.product([1.,3.,6.],[.01,.1],[0,60],[2500.,3500.]):
            for p in choices:
                for repeat in range(32):
                    i=len(rows);mask=int(p['Mask'])
                    truth=sum((np.random.default_rng(seed('truth',family,repeat)).random(20)<.5)*(1<<np.arange(20)))
                    meta=dict(ID=i,Family=family,Seed=6100,Budget=float(p['Budget']),Policy=p['Policy'],Mask=mask,TruthMask=int(truth),Horizon=H,Duty=duty,BackgroundNodes=bg,Radius=radius,Trial=repeat,Reservation=float(p['Reservation']))
                    rows.append(meta)
                    lines.append(f'{i} {mask} {longmask} {H} {duty} {bg} {radius} {seed("geometry",family)} {seed("background",family,repeat)}')
    write(dest/'Trial_Inputs.csv',rows);(dest/'trials.txt').write_text('\n'.join(lines)+'\n')
    print(f'Prepared {len(rows)} paired packet dispatches',flush=True)

def analyze():
    dest=ROOT/'work/packets';meta=list(csv.DictReader((dest/'Trial_Inputs.csv').open()))
    radio=list(csv.DictReader((dest/'Packet_Outputs.csv').open()));assert len(meta)==len(radio)
    tables={}
    for family in FAMILIES:
        t=np.load(ROOT/f'results/{family}_6100_terminal.npz')
        tables[family]=dict(zip(map(int,t['masks']),map(int,t['values'])))
    combined=[]
    for row,rx in zip(meta,radio):
        assert row['ID']==rx['ID'];mask=int(row['Mask']);got=int(rx['ReceivedMask']);truth=int(row['TruthMask'])
        assert got&~mask==0
        F=tables[row['Family']];actual=F[got&truth];perfect=F[mask&truth]
        assert actual<=perfect
        combined.append(dict(row,**{k:v for k,v in rx.items() if k!='ID'},ReceivedReports=got.bit_count(),Complete=int(got==mask),CertifiedFlow=actual,PerfectTimelyFlow=perfect,CommunicationLoss=perfect-actual))
    write(ROOT/'results/Packet_Dispatches.csv',combined)
    groups={}
    for r in combined:
        key=tuple(r[k] for k in ['Horizon','Duty','BackgroundNodes','Radius'])
        groups.setdefault(key,[]).append(r)
    summary=[]
    rng=np.random.default_rng(20261126)
    boot=rng.integers(0,32,(10000,32))
    for key,rows in groups.items():
        loss_by_trial=np.array([np.mean([r['CommunicationLoss'] for r in rows if int(r['Trial'])==i]) for i in range(32)])
        samples=loss_by_trial[boot].mean(axis=1);lo,hi=np.quantile(samples,[.025,.975])
        summary.append(dict(zip(['Horizon','Duty','BackgroundNodes','Radius'],key),Dispatches=len(rows),MeanReports=np.mean([r['ReceivedReports'] for r in rows]),CompleteFraction=np.mean([r['Complete'] for r in rows]),MeanFlow=np.mean([r['CertifiedFlow'] for r in rows]),MeanPerfectFlow=np.mean([r['PerfectTimelyFlow'] for r in rows]),MeanLoss=loss_by_trial.mean(),LossLower95=lo,LossUpper95=hi,MeanLate=np.mean([int(r['LateReplies']) for r in rows]),InterferenceEvents=sum(int(r['InterferenceEvents']) for r in rows),HalfDuplexEvents=sum(int(r['HalfDuplexEvents']) for r in rows)))
    write(ROOT/'results/Packet_Summary.csv',summary)
    print(f'Analyzed {len(combined)} dispatches, {len(summary)} settings',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','analyze']);a=p.parse_args()
    prepare() if a.action=='prepare' else analyze()
