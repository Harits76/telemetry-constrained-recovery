// Separate reference implementation: FIFO push-relabel and long-double expectations.
// Standard C++17 only. No original Python code or scientific-library dependency.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <string>
#include <vector>
using I=std::int64_t; using R=long double;
void require(bool p,const std::string& s){if(!p)throw std::runtime_error(s);}
struct Arc {int u,v,bit;I lo,hi;};
struct Edge {int to,next;};
struct Solver {
 int n,s,t;std::vector<Arc> arcs;std::vector<int> head,original;std::vector<Edge> edges;
 std::vector<I> residual,excess,capacity,balance;std::vector<int> height,current;std::vector<char> queued;
 std::queue<int> work;
 Solver(int N,int S,int T,const std::vector<Arc>& A):n(N),s(S),t(T),arcs(A),head(n,-1){
  for(const auto&a:arcs){require(a.u!=a.v,"self arc unsupported");original.push_back(edges.size());
   edges.push_back({a.v,head[a.u]});head[a.u]=edges.size()-1;
   edges.push_back({a.u,head[a.v]});head[a.v]=edges.size()-1;}
  residual.resize(edges.size());excess.resize(n);capacity.resize(arcs.size());balance.resize(n);
  height.resize(n);current.resize(n);queued.resize(n);
 }
 void activate(int u){if(u!=s&&u!=t&&excess[u]>0&&!queued[u]){work.push(u);queued[u]=true;}}
 void relabel_all(){
  std::fill(height.begin(),height.end(),n+1);height[t]=0;std::queue<int> bfs;bfs.push(t);
  while(!bfs.empty()){int u=bfs.front();bfs.pop();
   for(int e=head[u];e!=-1;e=edges[e].next){int v=edges[e].to;
    if(v!=s&&residual[e^1]>0&&height[v]==n+1){height[v]=height[u]+1;bfs.push(v);}}}
  height[s]=n;current=head;std::fill(queued.begin(),queued.end(),false);
  work=std::queue<int>();for(int u=0;u<n;++u)activate(u);
 }
 I solve(std::uint32_t mask,I& cutvalue){
  std::fill(residual.begin(),residual.end(),0);std::fill(excess.begin(),excess.end(),0);
  for(std::size_t j=0;j<arcs.size();++j){auto a=arcs[j];I c=(a.bit>=0&&(mask&(1u<<a.bit)))?a.hi:a.lo;
   require(c>=0,"negative capacity");capacity[j]=c;residual[original[j]]=c;}
  for(int e=head[s];e!=-1;e=edges[e].next){I x=residual[e];if(x){residual[e]-=x;residual[e^1]+=x;excess[s]-=x;excess[edges[e].to]+=x;}}
  relabel_all();int count=0;
  while(!work.empty()){
   int u=work.front();work.pop();queued[u]=false;
   while(excess[u]>0){
    int e=current[u];
    if(e==-1){int best=std::numeric_limits<int>::max();
     for(int a=head[u];a!=-1;a=edges[a].next)if(residual[a]>0)best=std::min(best,height[edges[a].to]);
     require(best!=std::numeric_limits<int>::max(),"stranded preflow");height[u]=best+1;current[u]=head[u];continue;}
    int v=edges[e].to;
    if(residual[e]>0&&height[u]==height[v]+1){I x=std::min(excess[u],residual[e]);residual[e]-=x;residual[e^1]+=x;excess[u]-=x;excess[v]+=x;activate(v);}
    else current[u]=edges[e].next;
   }
   if(++count>=n){relabel_all();count=0;}
  }
  // Verify primal feasibility on every original arc, independently of solver labels.
  std::fill(balance.begin(),balance.end(),0);
  for(std::size_t j=0;j<arcs.size();++j){I f=capacity[j]-residual[original[j]];
   require(f>=0&&f<=capacity[j],"flow capacity failure");balance[arcs[j].u]-=f;balance[arcs[j].v]+=f;}
  for(int u=0;u<n;++u)if(u!=s&&u!=t)require(balance[u]==0,"flow conservation failure");
  require(balance[t]==excess[t]&&balance[s]==-excess[t],"terminal balance failure");
  // Residual reachability supplies an integer cut upper witness for every state.
  std::vector<char> seen(n,false);std::vector<int> todo{s};seen[s]=true;
  while(!todo.empty()){int u=todo.back();todo.pop_back();
   for(int e=head[u];e!=-1;e=edges[e].next)if(residual[e]>0&&!seen[edges[e].to]){seen[edges[e].to]=true;todo.push_back(edges[e].to);}}
  require(!seen[t],"augmenting path remains");cutvalue=0;
  for(std::size_t j=0;j<arcs.size();++j)if(seen[arcs[j].u]&&!seen[arcs[j].v])cutvalue+=capacity[j];
  require(cutvalue==excess[t],"primal/dual values disagree");return excess[t];
 }
};
int main(int argc,char**argv){try{
 require(argc==3,"usage: full_truth INPUT.txt OUTPUT.bin");
 std::ifstream in(argv[1]); int n,E,s,t,m;in>>n>>E>>s>>t>>m;
 require(bool(in)&&m<=20,"bad graph");std::vector<Arc>A(E);
 for(auto&a:A)in>>a.u>>a.v>>a.lo>>a.hi>>a.bit;
 require(bool(in),"bad arcs");Solver solver(n,s,t,A);
 std::ofstream out(argv[2],std::ios::binary);require(bool(out),"output failure");
 for(std::uint32_t x=0;x<(1u<<m);++x){I cut,v=solver.solve(x,cut);
 require(v<=INT32_MAX,"int32 overflow");std::int32_t value=v;
 out.write(reinterpret_cast<const char*>(&value),4);}
 require(bool(out),"write failure");std::cout<<"verified_states="<<(1u<<m)<<std::endl;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
