"""Observable trace diagnostics and a separate event-level service check."""
from pathlib import Path
import json,csv,itertools
import numpy as np
from reference_engine import arrivals
ROOT=Path(__file__).resolve().parents[1]
def write(name,rows):
    with (ROOT/'results'/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def event_arrival(reply,duty,backhaul,turnaround,busy):
    # Integer-microsecond reservation simulator, with explicit gateway events.
    tick=lambda t:int(round(t*1e6))
    hd=tick(.046336);request_ready=tick(backhaul/2+busy);events=[];next_legal=0;now=0
    for seconds in reply:
        now=max(now,request_ready,next_legal)
        events.append(('downlink_start',now));next_legal=now+int(round(hd/duty))
        now+=hd;events.append(('downlink_end',now))
        now+=tick(turnaround);events.append(('reply_start',now))
        now+=tick(seconds);events.append(('reply_end',now))
        request_ready=now
    return (now+tick(backhaul/2))/1e6 if len(reply) else 0.,events
def main():
    data=np.load(ROOT/'data/trace_blocks.npz');rows=[];masks=data['masks'];air=data['airtimes'];observed=data['observed']
    for sensor in sorted(set(data['sensor'])):
        pick=data['sensor']==sensor;bits=(masks[pick]&1)>0;training=data['train_prr'][pick];assert np.max(training)==np.min(training)
        p=float(training[0]);perblock=bits.mean(axis=1);q=float(bits.mean());obs=observed[pick];actual_air=air[pick][obs]
        h=float(data['train_airtime'][pick][0])
        rows.append(dict(Sensor=str(sensor),Blocks=int(pick.sum()),Opportunities=int(bits.size),TrainPRR=p,TestPRR=q,Shift=q-p,BlockMAE=float(np.mean(np.abs(perblock-p))),Brier=float(np.mean((bits-p)**2)),TrainingMedianAirtime=h,ObservedTestFrames=int(obs.sum()),TestMedianAirtime=float(np.median(actual_air)),WithinTrainingDuration=float(np.mean(actual_air<=h+1e-12)),Test95Airtime=float(np.quantile(actual_air,.95,method='higher'))))
    write('Trace_Transport_Diagnostic.csv',rows)
    service=[];maximum_error=0.
    for k in range(1,7):
        for pattern in itertools.product([.056576,.066816],repeat=k):
            for duty,bh,turn,busy in itertools.product([.01,.1],[.05,.5,2.5],[.001,.01,.1],[0.,.5]):
                for order,h in [('ID',pattern),('REVERSE',pattern[::-1])]:
                    literal,events=event_arrival(h,duty,bh,turn,busy)
                    s=dict(downlink=.046336,duty=duty,backhaul=bh,turnaround=turn)
                    analytic=float(arrivals(np.array([(1<<k)-1]),np.array(h),s)[0])+busy
                    error=abs(literal-analytic);maximum_error=max(maximum_error,error);assert error<1e-10
                    for horizon in [.63,1.095,3.]:
                        eligible=literal<=horizon+1e-12
                        service.append(dict(Reports=k,Pattern=''.join('S' if x<.06 else 'L' for x in pattern),Order=order,Duty=duty,Backhaul=bh,Turnaround=turn,InitialBusy=busy,Horizon=horizon,Arrival=literal,Eligible=eligible,AnalyticalArrival=analytic,AbsoluteError=error))
    write('Event_Service_Check.csv',service)
    record=dict(sensors=len(rows),blocks=sum(r['Blocks'] for r in rows),opportunities=sum(r['Opportunities'] for r in rows),weighted_train_prr=sum(r['TrainPRR']*r['Opportunities'] for r in rows)/sum(r['Opportunities'] for r in rows),weighted_test_prr=sum(r['TestPRR']*r['Opportunities'] for r in rows)/sum(r['Opportunities'] for r in rows),mean_sensor_abs_shift=float(np.mean([abs(r['Shift']) for r in rows])),minimum_shift=min(r['Shift'] for r in rows),maximum_shift=max(r['Shift'] for r in rows),service_rows=len(service),maximum_service_error=maximum_error,scope='Transport diagnostic of previously used environmental traces; separate implementation check of the declared service contract. No measured logistics capacities or two-way exchange observations; metadata transport and computational consistency only.')
    (ROOT/'results/Communication_Audit.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
