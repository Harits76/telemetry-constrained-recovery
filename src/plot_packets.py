"""Vector communication figure with 18-point bold source labels."""
from pathlib import Path
import os,csv,collections
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'work/mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({'font.size':18,'font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold','axes.titlesize':18,'axes.labelsize':18,'xtick.labelsize':18,'ytick.labelsize':18,'legend.fontsize':18,'pdf.fonttype':42,'savefig.bbox':'tight'})
S=list(csv.DictReader((ROOT/'results/Service_Optima.csv').open()))
P=list(csv.DictReader((ROOT/'results/Packet_Summary.csv').open()))
fig,axs=plt.subplots(1,2,figsize=(14.4,5.6))
for duty,color,marker,label in [(.1,'#172F53','o','10% duty'),(.01,'#D1495B','s','1% duty')]:
    y=[np.mean([float(r['IdealServiceOptimum']) for r in S if float(r['Duty'])==duty and float(r['Horizon'])==H]) for H in [1,3,6]]
    axs[0].plot([0,1,2],y,color=color,marker=marker,lw=2.3,label=label)
    for x,v in enumerate(y):axs[0].annotate(f'{v:.1f}',(x,v),xytext=(0,10 if duty==.1 else -23),textcoords='offset points',ha='center',fontsize=18,weight='bold',color=color)
axs[0].set_xticks([0,1,2],['1','3','6']);axs[0].set_xlabel('Dispatch horizon (s)')
axs[0].set_ylabel('Service-adapted exact flow\n(model units/dispatch)')
axs[0].set_title('(a) Perfect-reception reference');axs[0].set_ylim(215,445);axs[0].grid(alpha=.2);axs[0].legend(loc='upper left')
for bg,shift,color,label in [(0,-.19,'#51799A','Quiet'),(60,.19,'#D1495B','10 uplinks/s')]:
    rows=[next(r for r in P if float(r['Horizon'])==3 and float(r['Duty'])==.1 and int(r['BackgroundNodes'])==bg and float(r['Radius'])==radius) for radius in [2500,3500]]
    y=np.array([float(r['MeanLoss']) for r in rows]);lower=np.array([float(r['LossLower95']) for r in rows]);upper=np.array([float(r['LossUpper95']) for r in rows]);x=np.arange(2)+shift
    axs[1].bar(x,y,width=.36,color=color,label=label,yerr=np.array([y-lower,upper-y]),capsize=5)
    for xx,v,top in zip(x,y,upper):axs[1].text(xx,top+3,f'{v:.1f}',ha='center',fontsize=18,weight='bold')
axs[1].set_xticks([0,1],['2.5 km','3.5 km']);axs[1].set_xlabel('Maximum simulated radius')
axs[1].set_ylabel('Same-batch communication loss\n(model units/dispatch)')
axs[1].set_title('(b) Packet outcomes at H = 3 s');axs[1].set_ylim(0,106);axs[1].grid(axis='y',alpha=.2);axs[1].set_axisbelow(True);axs[1].legend(loc='upper left')
fig.subplots_adjust(left=.08,right=.99,wspace=.35,bottom=.17,top=.90)
dest=ROOT/'paper/figures';dest.mkdir(parents=True,exist_ok=True)
fig.savefig(dest/'CommunicationEffects.pdf');plt.close(fig)
