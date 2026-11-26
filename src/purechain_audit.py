"""Original-notebook-style PureChain audit log (collector side, no consensus).

Canonical UTF-8 JSON, SHA-256 payload/block hashes and previous-hash links
retain the original notebook's block format. Logical replay timestamps are
not observations of execution time. A supplied checkpoint must be trusted
independently to detect a consistent rewrite of both log and checkpoint.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import gzip, hashlib, json, math, time, zlib

ZERO = '0' * 64
EPOCH = datetime(2026, 11, 26, tzinfo=timezone.utc)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def csv_record(row):
    out={}
    for key,value in row.items():
        if isinstance(value,float) and not math.isfinite(value):
            raise ValueError('Nonfinite audit value')
        out[str(key)]='' if value is None else str(value)
    return out

def block(index, previous, identity, payload, kind='EXPERIMENT'):
    out=dict(BlockIndex=index,BlockType=kind,
             Timestamp=(EPOCH+timedelta(microseconds=index)).isoformat(timespec='microseconds'),
             ExperimentID=identity,PreviousHash=previous,Payload=payload,
             PayloadHash=digest(payload))
    out['BlockHash']=digest(out)
    return out

def policy_id(row):
    return 'policy/'+'/'.join(str(row[k]) for k in
        ['Cohort','Family','Seed','Prior','Reception'])+f"/{float(row['Budget']):.2f}/{row['Policy']}"

def packet_id(row):
    return f"packet/{int(row['ID'])}"

class PureChainWriter:
    def __init__(self,path,expected_ids,context):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.expected=set(expected_ids)
        if len(self.expected)!=len(expected_ids):raise ValueError('Duplicate expected experiment ID')
        self.ids_hash=digest(sorted(self.expected));self.context_hash=digest(context)
        self.partial=self.path.with_name(self.path.name+'.partial')
        self.raw=self.partial.open('wb')
        self.stream=gzip.GzipFile(filename='',fileobj=self.raw,mode='wb',mtime=0)
        self.seen=set();self.previous=ZERO;self.count=0;self.append_ns=[];self.finished=False
        genesis=block(0,ZERO,'GENESIS',dict(
            Chain='PureChain',Implementation='Original-notebook-style local audit ledger',
            SchemaVersion=1,HashAlgorithm='SHA-256',ExperimentCount=len(self.expected),
            ExpectedIDsHash=self.ids_hash,ContextHash=self.context_hash,Context=context,
            TimestampSemantics='Logical replay ticks; not physical execution times',
            Scope='Collector-side audit; no signatures, consensus or sensor authentication'),
            kind='GENESIS')
        self._write(genesis);self.genesis_hash=genesis['BlockHash']

    def _write(self,value):
        self.stream.write(canonical(value)+b'\n');self.previous=value['BlockHash']

    def append(self,identity,payload):
        if self.finished:raise ValueError('Ledger already closed')
        if identity not in self.expected:raise ValueError('Unexpected experiment ID')
        if identity in self.seen:raise ValueError('Duplicate experiment ID')
        started=time.perf_counter_ns()
        value=block(self.count+1,self.previous,identity,payload)
        self._write(value);self.seen.add(identity);self.count+=1
        self.append_ns.append(time.perf_counter_ns()-started)

    def finish(self):
        if self.seen!=self.expected:raise ValueError('Missing expected experiment records')
        started=time.perf_counter_ns();self.stream.close();self.raw.close()
        self.partial.replace(self.path);self.finished=True
        checkpoint=dict(SchemaVersion=1,LedgerFile=self.path.name,
            ExperimentCount=self.count,GenesisHash=self.genesis_hash,
            TailHash=self.previous,ContextHash=self.context_hash,
            ExpectedIDsHash=self.ids_hash,LedgerSHA256=file_digest(self.path))
        self.path.with_name(self.path.name+'.checkpoint.json').write_bytes(canonical(checkpoint)+b'\n')
        times=sorted(self.append_ns)
        def quantile(p):return times[min(len(times)-1,int(p*(len(times)-1)))]/1e6 if times else None
        performance=dict(ExperimentCount=self.count,StoredBytes=self.path.stat().st_size,
            AppendSeconds=sum(times)/1e9,AppendMedianMs=quantile(.5),AppendP95Ms=quantile(.95),
            FinalizeSeconds=(time.perf_counter_ns()-started)/1e9,
            Scope='Observed host encode/hash/compress/write cost; no fsync, device or consensus latency')
        self.path.with_name(self.path.name+'.performance.json').write_bytes(canonical(performance)+b'\n')
        return checkpoint

    def abort(self):
        if not self.finished:
            self.stream.close();self.raw.close()

    def __enter__(self):return self
    def __exit__(self,kind,value,trace):
        if kind is not None:self.abort()
        elif not self.finished:
            try:self.finish()
            except Exception:self.abort();raise

def read_blocks(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        for line in stream:yield json.loads(line)

def verify(path,expected_ids,checkpoint,context=None,expected_payloads=None):
    """Check a log against separately supplied expectations/checkpoint.

    This checks consistency with supplied evidence, not its independent trust.
    expected_payloads is optional and should come from a separate CSV replay.
    """
    expected=set(expected_ids);errors=[];seen=set();verified=set();previous=ZERO
    genesis_hash=None;genesis_context=None;count=0;total=0
    if len(expected)!=len(expected_ids):errors.append('Duplicate expected IDs')
    try:
        for index,current in enumerate(read_blocks(path)):
            total+=1;before=len(errors)
            if current.get('BlockIndex')!=index:errors.append('Block index mismatch')
            if current.get('PreviousHash')!=previous:errors.append('Previous hash mismatch')
            if current.get('PayloadHash')!=digest(current.get('Payload')):errors.append('Payload hash mismatch')
            if current.get('BlockHash')!=digest({k:v for k,v in current.items() if k!='BlockHash'}):errors.append('Block hash mismatch')
            identity=current.get('ExperimentID');payload=current.get('Payload',{})
            if index==0:
                genesis_hash=current.get('BlockHash');genesis_context=payload.get('ContextHash')
                if current.get('BlockType')!='GENESIS' or identity!='GENESIS':errors.append('Invalid genesis')
                if payload.get('ExperimentCount')!=len(expected):errors.append('Genesis count mismatch')
                if payload.get('ExpectedIDsHash')!=digest(sorted(expected)):errors.append('Genesis expected-ID mismatch')
                if payload.get('ContextHash')!=digest(payload.get('Context')):errors.append('Genesis context hash mismatch')
                if context is not None and payload.get('ContextHash')!=digest(context):errors.append('Expected context mismatch')
            else:
                count+=1
                if current.get('BlockType')!='EXPERIMENT':errors.append('Invalid experiment block type')
                if identity not in expected:errors.append('Unexpected experiment ID')
                if identity in seen:errors.append('Duplicate experiment ID')
                seen.add(identity)
                if expected_payloads is not None and payload!=expected_payloads.get(identity):errors.append('Payload/source record mismatch')
                if len(errors)==before:verified.add(identity)
            previous=current.get('BlockHash')
    except (OSError,ValueError,KeyError,TypeError,AttributeError,EOFError,zlib.error) as exc:
        errors.append('Unreadable ledger: '+type(exc).__name__)
    if not total:errors.append('Empty ledger')
    if seen!=expected:errors.append('Missing or unexpected records')
    if count!=len(expected):errors.append('Experiment count mismatch')
    try:storage_hash=file_digest(path)
    except OSError:storage_hash=None
    checks=dict(ExperimentCount=count,GenesisHash=genesis_hash,TailHash=previous,
                ContextHash=genesis_context,ExpectedIDsHash=digest(sorted(expected)),
                LedgerSHA256=storage_hash)
    for key,value in checks.items():
        if checkpoint.get(key)!=value:errors.append('Checkpoint mismatch: '+key)
    return dict(Valid=not errors,ExperimentBlocks=count,GenesisBlocks=int(bool(total)),
        ExpectedExperiments=len(expected),VerifiedExperiments=len(verified&expected),
        AuditCoverage=len(verified&expected)/len(expected) if expected else None,
        TailHash=previous,Errors=errors,
        Trust='Consistency against supplied checkpoint; producer/input authenticity and consensus unverified')
