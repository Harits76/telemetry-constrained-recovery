"""Build pinned public ns-3 and LoRa sources with the companion application."""
from pathlib import Path
import argparse,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
work=ROOT/'work';work.mkdir(exist_ok=True);ns=work/'ns-3';module=ns/'contrib/lorawan'
def run(args,cwd=None):subprocess.run(args,cwd=cwd,check=True)
if not ns.exists():run(['git','clone','--depth','1','--branch','ns-3.48','https://gitlab.com/nsnam/ns-3-dev.git',str(ns)])
if not module.exists():run(['git','clone','https://github.com/signetlabdei/lorawan.git',str(module)])
for path,commit in [(ns,'d2add90b452d600cfb4859baed8e9ea633519447'),(module,'e45b4af428c92f30b2e6c201055809110758125f')]:
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=path,text=True).strip()!=commit:
        run(['git','fetch','origin',commit],path);run(['git','checkout','--detach',commit],path)
shutil.copy2(ROOT/'ns3/telemetry-packets.cc',ns/'scratch/telemetry-packets.cc')
run(['./ns3','configure','--build-profile=release','--enable-tests','--disable-examples','--enable-modules=lorawan','--enable-asserts'],ns)
run(['./ns3','build','telemetry-packets','test-runner','-j',str(a.jobs)],ns)
print(ns/'build/scratch/ns3.48-telemetry-packets')
