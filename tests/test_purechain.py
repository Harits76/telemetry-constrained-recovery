"""Integrity, completeness, deterministic replay and explicit trust boundary."""
from pathlib import Path
import copy,gzip,json,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from purechain_audit import PureChainWriter,verify,read_blocks,canonical,block,file_digest,digest

fixture=json.loads((Path(__file__).parent/'data/purechain_reference.json').read_text())
for value in fixture['Blocks']:
    assert digest(value['Payload'])==value['PayloadHash']
    assert digest({k:v for k,v in value.items() if k!='BlockHash'})==value['BlockHash']

with tempfile.TemporaryDirectory() as name:
    root=Path(name);ids=['run/0','run/1'];ctx={'InputSHA256':'a'*64}
    payloads={'run/0':{'Flow':10,'Label':'capacity-α'},'run/1':{'Flow':20}}
    paths=[]
    for label in ['first','repeat']:
        path=root/(label+'.jsonl.gz')
        with PureChainWriter(path,ids,ctx) as writer:
            for identity in ids:writer.append(identity,payloads[identity])
        paths.append(path)
    assert paths[0].read_bytes()==paths[1].read_bytes()
    checkpoint=json.loads(paths[0].with_name(paths[0].name+'.checkpoint.json').read_text())
    result=verify(paths[0],ids,checkpoint,ctx,payloads)
    assert result['Valid'] and result['AuditCoverage']==1 and result['ExperimentBlocks']==2 and result['GenesisBlocks']==1
    chain=list(read_blocks(paths[0]));cases={}
    changed=copy.deepcopy(chain);changed[1]['Payload']['Flow']=999;cases['payload edit']=changed
    changed=copy.deepcopy(chain);changed[1]['PayloadHash']='0'*64;cases['payload hash edit']=changed
    changed=copy.deepcopy(chain);changed[2]['PreviousHash']='0'*64;cases['broken link']=changed
    cases['delete middle']=[chain[0],chain[2]]
    cases['truncate suffix']=chain[:-1]
    cases['reorder']=[chain[0],chain[2],chain[1]]
    changed=copy.deepcopy(chain);changed[2]['ExperimentID']='run/0';cases['duplicate ID']=changed
    changed=copy.deepcopy(chain);changed.append(copy.deepcopy(chain[-1]));cases['extra record']=changed
    cases['genesis only']=chain[:1]
    def save(label,values):
        path=root/(label+'.gz')
        with path.open('wb') as raw:
            with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:
                for value in values:stream.write(canonical(value)+b'\n')
        return path
    for label,values in cases.items():assert not verify(save(label,values),ids,checkpoint,ctx,payloads)['Valid'],label
    genesis_result=verify(save('genesis',chain[:1]),ids,checkpoint,ctx,payloads)
    assert genesis_result['AuditCoverage']==0
    corrupt=root/'corrupt.gz';corrupt.write_bytes(paths[0].read_bytes()[:20])
    assert not verify(corrupt,ids,checkpoint,ctx,payloads)['Valid']
    # Recompute every hash after changing a result: a retained checkpoint detects it.
    forged=[chain[0]]
    for current in chain[1:]:
        value=copy.deepcopy(current['Payload']);value['Flow']+=100
        forged.append(block(len(forged),forged[-1]['BlockHash'],current['ExperimentID'],value))
    path=save('fully-rehashed',forged)
    assert not verify(path,ids,checkpoint,ctx)['Valid']
    # Replacing the checkpoint as well defeats unauthenticated local consistency.
    replaced=dict(checkpoint,TailHash=forged[-1]['BlockHash'],LedgerSHA256=file_digest(path))
    assert verify(path,ids,replaced,ctx)['Valid']
    assert not verify(path,ids,replaced,ctx,payloads)['Valid']
    try:
        with PureChainWriter(root/'incomplete.gz',ids,ctx) as writer:writer.append(ids[0],payloads[ids[0]])
        raise AssertionError('Incomplete run accepted')
    except ValueError:pass
    with PureChainWriter(root/'duplicate.gz',[ids[0]],ctx) as writer:
        writer.append(ids[0],payloads[ids[0]])
        try:writer.append(ids[0],payloads[ids[0]]);raise AssertionError('Duplicate append accepted')
        except ValueError:pass
    with PureChainWriter(root/'empty.gz',[],ctx):pass
    empty_cp=json.loads((root/'empty.gz.checkpoint.json').read_text())
    assert verify(root/'empty.gz',[],empty_cp,ctx)['AuditCoverage'] is None
print('PASS: valid/replay, 10 corruption/completeness cases, rewrite anchoring and explicit local-trust limitation')
