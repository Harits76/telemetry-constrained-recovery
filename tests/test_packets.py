"""Known feasible, duty-limited, late and unreachable packet exchanges."""
import csv,subprocess,sys,tempfile
from pathlib import Path
binary=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as name:
    root=Path(name);inp=root/'smoke.txt';out=root/'smoke.csv'
    inp.write_text('0 63 42 3 .1 0 500 42 43\n1 63 42 3 .01 0 500 42 43\n2 63 42 1 .1 0 500 42 43\n3 63 42 6 .01 0 500 42 43\n4 63 42 3 .1 60 2500 42 43\n5 63 42 3 .1 0 1000000000 42 43\n')
    args=[str(binary),'--input='+str(inp),'--output='+str(out)]
    subprocess.run(args,check=True);first=out.read_bytes()
    rows=list(csv.DictReader(out.open()))
    assert [int(r['ReceivedMask']) for r in rows[:4]]==[63,1,3,3]
    assert int(rows[2]['LateReplies'])==1
    assert int(rows[5]['ReceivedMask'])==0 and int(rows[5]['Replies'])==0
    assert int(rows[4]['BackgroundTransmissions'])>0
    assert int(rows[4]['InterferenceEvents'])>0
    assert int(rows[4]['HalfDuplexEvents'])>0
    assert abs(float(rows[0]['LastReplySeconds'])-2.489952)<.00001
    subprocess.run(args,check=True);assert out.read_bytes()==first
print('PASS: quiet, duty, deadline, interference, half duplex, unreachable, ToA and deterministic replay checks')
