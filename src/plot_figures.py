from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[1];os.environ['MPLCONFIGDIR']=str(ROOT/'build/mpl')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Circle
import numpy as np,pandas as pd
F=ROOT/'paper/figures';F.mkdir(exist_ok=True,parents=True);R=ROOT/'results'
plt.rcParams.update({'font.size':18,'font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold','axes.titlesize':18,'axes.labelsize':18,'xtick.labelsize':18,'ytick.labelsize':18,'legend.fontsize':18,'pdf.fonttype':42,'savefig.bbox':'tight'})
# Clear causal boundary; full canvas preserves space for18ptlabels.
fig,ax=plt.subplots(figsize=(12.4,4.3));ax.set_position([0,0,1,1]);ax.set_xlim(0,12.4);ax.set_ylim(0,4.3);ax.axis('off')
boxes=[(.1,2.1,2.7,1.6,'Capacity sensors\nEngineering bounds\nReport outcomes'),(3.3,2.1,2.6,1.6,'Radio / delivery\nNative costs\nDuty + deadline'),(6.4,2.1,2.6,1.6,'Received reports\nCertified bounds\nNo hidden state'),(9.5,2.1,2.7,1.6,'Recovery flow\nShared routes\nFlow certificate')]
for x,y,w,h,text in boxes:ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',facecolor='#EEF4F8',edgecolor='#172F53',lw=1.5));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=18,weight='bold',linespacing=1.5)
for x in [2.85,5.95,9.05]:ax.add_patch(FancyArrowPatch((x,2.9),(x+.38,2.9),arrowstyle='-|>',mutation_scale=15,lw=1.7,color='#172F53'))
ax.add_patch(FancyBboxPatch((3.3,.15),5.7,1.15,boxstyle='round,pad=.08',facecolor='#FAF0D9',edgecolor='#8B681A',lw=1.5));ax.text(6.15,.72,'One-shot batch selection\nCut / singleton knapsack\nComplete offline reference',ha='center',va='center',fontsize=18,weight='bold')
ax.text(1.45,.72,'Priors + bounds\nTraining metadata\nBudget + horizon',ha='center',va='center',fontsize=18,weight='bold')
ax.add_patch(FancyArrowPatch((2.85,.72),(3.20,.72),arrowstyle='-|>',mutation_scale=15,lw=1.7,color='#172F53'))
ax.add_patch(FancyArrowPatch((4.6,1.4),(4.6,2.02),arrowstyle='-|>',mutation_scale=15,lw=1.7,color='#172F53'))
ax.add_patch(FancyBboxPatch((9.5,.15),2.7,1.15,boxstyle='round,pad=.08',facecolor='#F2F2F2',edgecolor='#59636D',lw=1.3))
ax.text(10.85,.72,'PureChain audit\nDecision + flow log\nIntegrity checks',ha='center',va='center',fontsize=18,weight='bold')
ax.add_patch(FancyArrowPatch((10.85,2.02),(10.85,1.42),arrowstyle='-|>',mutation_scale=15,lw=1.3,color='#59636D'))
ax.add_patch(FancyArrowPatch((9.1,.72),(9.4,.72),arrowstyle='-|>',mutation_scale=13,lw=1.1,linestyle='--',color='#59636D'))
ax.text(10.85,4.05,'Truth: evaluation only',ha='center',va='center',fontsize=18,weight='bold',color='#9F3242');fig.savefig(F/'DecisionLoop.pdf');plt.close(fig)
# Small exact examples expose why a general submodular guarantee is unavailable.
fig,axs=plt.subplots(1,2,figsize=(12.4,4.6))
def node(ax,x,y,label):ax.add_patch(Circle((x,y),.18,facecolor='#EEF4F8',edgecolor='#172F53',lw=1.5));ax.text(x,y,label,ha='center',va='center',weight='bold',fontsize=18)
def edge(ax,a,b,label,dx=0,dy=.22):
 v=np.array(b)-np.array(a);v=v/np.linalg.norm(v);aa=np.array(a)+.20*v;bb=np.array(b)-.20*v;ax.add_patch(FancyArrowPatch(aa,bb,arrowstyle='-|>',mutation_scale=15,lw=1.5,color='#172F53'));mid=(np.array(a)+np.array(b))/2;ax.text(mid[0]+dx,mid[1]+dy,label,ha='center',va='center',fontsize=18,weight='bold')
for ax in axs:ax.set_xlim(0,6);ax.set_ylim(0,3.5);ax.axis('off')
axs[0].set_title('(a) Serial complementarity');node(axs[0],.6,2.3,'s');node(axs[0],3,2.3,'v');node(axs[0],5.4,2.3,'t');edge(axs[0],(.6,2.3),(3,2.3),'X1');edge(axs[0],(3,2.3),(5.4,2.3),'X2');axs[0].text(3,.75,'J({1}) = J({2}) = 0\nJ({1,2}) = 0.25',ha='center',va='center',weight='bold',fontsize=18,linespacing=1.6)
axs[1].set_title('(b) Parallel saturation');pts={'s':(.4,2.1),'a':(2,3),'b':(2,1.2),'z':(3.9,2.1),'t':(5.6,2.1)}
for key,(x,y) in pts.items():node(axs[1],x,y,key)
for a,b,label,dy in [('s','a','X1',.22),('s','b','X2',-.22),('a','z','1',.15),('b','z','1',-.15),('z','t','1',.25)]:edge(axs[1],pts[a],pts[b],label,dy=dy)
axs[1].text(3,.25,'J({1}) = J({2}) = 0.50\nJ({1,2}) = 0.75',ha='center',va='center',fontsize=18,weight='bold',linespacing=1.6);fig.tight_layout();fig.savefig(F/'ObjectiveProperties.pdf');plt.close(fig)
a=pd.read_csv(R/'Policy_Exact_Summary.csv');policies=['CUT','CUT_DP','MYOPIC_FLOW','LAZY_GREEDY','LOCAL_SWAP','MODULAR_DP'];labels=['Cut ranking','Cut knapsack','Static gain','Greedy gain','Exchange','Singleton knapsack'];priors=['I05','HETERO','CORRELATED'];matrices=[]
for budget in [.42,.7]:matrices.append(np.array([[a[(a.Prior==pr)&(a.Budget==budget)&(a.Policy==policy)].MeanExactGap.mean() for pr in priors] for policy in policies]))
fig,axs=plt.subplots(1,2,figsize=(14.4,5.2));vmax=max(float(M.max()) for M in matrices)
for ax,M,b in zip(axs,matrices,[.42,.7]):
 im=ax.imshow(M,cmap='YlOrRd',vmin=0,vmax=vmax,aspect='auto');ax.set_title(f'Budget {b:.2f} s');ax.set_xticks(range(3),['Equal 0.5','Unequal','Correlated']);ax.set_yticks(range(6),labels if ax is axs[0] else []);ax.tick_params(axis='x',rotation=22);plt.setp(ax.get_xticklabels(),ha='right')
 for i in range(6):
  for j in range(3):ax.text(j,i,f'{M[i,j]:.3f}',ha='center',va='center',fontsize=18,weight='bold',color='white' if M[i,j]>.6*vmax else '#172F53')
fig.subplots_adjust(left=.23,right=.89,wspace=.28,bottom=.22);cax=fig.add_axes([.92,.18,.02,.70]);fig.colorbar(im,cax=cax).set_label('Mean exact gap\n(model units/dispatch)');fig.savefig(F/'ExactPolicyGaps.pdf');plt.close(fig)
w=pd.read_csv(R/'Width_Summary.csv');fig,axs=plt.subplots(1,2,figsize=(12.4,4.7))
for ax,m in zip(axs,[8,20]):
 z=w[w.Candidates==m].sort_values('WidthFraction');N=int(z.N.iloc[0]);xx=np.arange(len(z));ax.bar(xx,z.NontrivialCertificates,width=.65,color='#51799A');ax.set_title(f'{m} resources (N = {N})');ax.set_xlabel('Width fraction (five scenarios)');ax.set_xticks(xx,['0.05','0.10','0.25','0.50','1.00']);ax.set_ylabel('Nonconstant certified cases');ax.set_ylim(0,1.14*N);ax.set_axisbelow(True);ax.grid(axis='y',alpha=.2)
 for x,count in zip(xx,z.NontrivialCertificates):ax.annotate(str(int(count)),(x,count),xytext=(0,7),textcoords='offset points',ha='center',weight='bold',fontsize=18)
fig.tight_layout();fig.savefig(F/'StructuralApplicability.pdf');plt.close(fig)
