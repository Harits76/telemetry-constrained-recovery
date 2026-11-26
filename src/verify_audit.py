"""Verify PureChain against input identities, CSV results and a checkpoint."""
from pathlib import Path
import argparse,csv,json
from audit_adapter import policy_expectations,context,policy_payload,packet_payload
from purechain_audit import policy_id,packet_id,verify
ROOT=Path(__file__).resolve().parents[1]
def read(path):
    with Path(path).open(newline='') as stream:return list(csv.DictReader(stream))
def condition(row):return tuple(str(row[k]) for k in ['Cohort','Family','Seed','Prior','Reception'])+(float(row['Budget']),)
def check(kind,cohort='all',anchor=None):
    if kind=='allocation':
        paths=sorted((ROOT/'cases').glob(('*' if cohort=='all' else cohort)+'/*.json'))
        ids=policy_expectations(paths);expected_context=context('allocation',paths+[ROOT/'data/full_truth.npz'])
        rows=read(ROOT/f'results/{cohort}_Policies.csv');refs={condition(r):r for r in read(ROOT/f'results/{cohort}_Optima.csv')}
        payloads={policy_id(r):policy_payload(r,refs[condition(r)]) for r in rows}
        path=ROOT/f'results/purechain/{cohort}_Allocation.jsonl.gz'
    else:
        dest=ROOT/'work/packets';meta=read(dest/'Trial_Inputs.csv');ids=[packet_id(r) for r in meta]
        families=['anaheim','berlin','massachusetts','barcelona','ER64','GRID64']
        inputs=[dest/'Trial_Inputs.csv',dest/'Packet_Outputs.csv']+[ROOT/f'results/{f}_6100_terminal.npz' for f in families]
        expected_context=context('packet',inputs);rows=read(ROOT/'results/Packet_Dispatches.csv')
        payloads={packet_id(r):packet_payload(r) for r in rows};path=ROOT/'results/purechain/Packet_Dispatches.jsonl.gz'
    if len(payloads)!=len(rows):raise ValueError('Duplicate source CSV identities')
    checkpoint=json.loads(path.with_name(path.name+'.checkpoint.json').read_text())
    if anchor is not None:
        anchored=json.loads(Path(anchor).read_text())
        checkpoint=anchored[kind] if kind in anchored else anchored
    result=verify(path,ids,checkpoint,expected_context,payloads)
    result['CheckpointProvenance']=('Caller-supplied anchor; trust depends on its provenance' if anchor is not None else 'Adjacent checkpoint; compare its head with the public release for independent anchoring')
    path.with_name(path.name+'.verification.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['Valid']:raise ValueError(json.dumps(result))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['allocation','packet','both'],default='both');p.add_argument('--cohort',choices=['original','test','all'],default='all');p.add_argument('--anchor',type=Path);a=p.parse_args()
    for kind in (['allocation','packet'] if a.kind=='both' else [a.kind]):print(kind,json.dumps(check(kind,a.cohort,a.anchor),indent=2))
