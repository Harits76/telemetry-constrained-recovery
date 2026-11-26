"""PureChain payloads for the existing collector-side experiment records."""
from pathlib import Path
import json
from purechain_audit import csv_record, file_digest, policy_id, packet_id
ROOT=Path(__file__).resolve().parents[1]
RULES=['CUT','RANDOM','MYOPIC_FLOW','LAZY_GREEDY','LOCAL_SWAP','MODULAR_DP','CUT_DP','FLOW_MSE','SUMMARY_VOI']

def commitments(paths):
    return {str(Path(p).relative_to(ROOT)):file_digest(p) for p in sorted(map(Path,paths))}

def policy_expectations(paths):
    ids=[]
    for path in paths:
        c=json.loads(Path(path).read_text())
        for prior in c['capacity']:
            for reception in c['reception']:
                for B in [.28,.42,.7]:
                    for rule in RULES:
                        ids.append(policy_id(dict(Cohort=c['cohort'],Family=c['family'],Seed=c['seed'],Prior=prior,Reception=reception,Budget=B,Policy=rule)))
    return ids

def context(kind,inputs):
    files=[ROOT/'src'/n for n in ['purechain_audit.py','audit_adapter.py','reference_engine.py','policies.py','information.py']]
    files.append(ROOT/'src'/('run_study.py' if kind=='allocation' else 'packet_experiment.py'))
    return dict(Study='Telemetry-Constrained Recovery Allocation',Mode=kind,
        Backend='Original-notebook-style PureChain local audit ledger',
        Inputs=commitments(inputs),Code=commitments(files),
        DecisionRole='Collector-side recording after evaluation; no optimizer or radio feedback',
        TruthMaskRole='Simulation-only evaluation state; not available to query selection')

def policy_payload(row,reference):
    return dict(Operation='expected-allocation-evaluation',Record=csv_record(row),
                Reference=csv_record(reference))

def packet_payload(row):
    got=int(row['ReceivedMask']);truth=int(row['TruthMask'])
    return dict(Operation='packet-allocation-evaluation',Record=csv_record(row),
        ControllerObservations=dict(ReceivedMask=got,ReceivedHighMask=got&truth),
        TruthMaskRole='Simulation-only evaluation state; not controller input')
