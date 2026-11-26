/* SPDX-License-Identifier: GPL-2.0-only
 * Query/reply experiment using the Padova ns-3 LoRa PHY implementation.
 * Continuous listening is emulated with gapless rearmed RXSINGLE operations.
 * This is an application scheduler with explicit duty accounting, not a
 * LoRaWAN MAC conformance implementation (no join, ADR, MIC or RX1 procedure).
 */
#include "ns3/core-module.h"
#include "ns3/mobility-module.h"
#include "ns3/propagation-module.h"
#include "ns3/lorawan-module.h"
#include <fstream>
#include <iomanip>
#include <random>
#include <vector>
using namespace ns3;
using namespace ns3::lorawan;
struct Trial {
 std::vector<Ptr<SimpleEndDeviceLoraPhy>> ed,bg;
 Ptr<SimpleGatewayLoraPhy> gw; Ptr<LoraChannel> channel;
 uint32_t mask=0,longmask=0,received=0; double H=3,duty=.1;
 int requests=0,replies=0,late=0,bgSent=0,interfered=0,halfduplex=0,under=0;
 double last=-100,lastReply=0; LoraTxParameters down,up;
};
void Listen(Trial*t,int i);
void TxDone(Trial*t,int i,Ptr<const Packet>p){Listen(t,i);}
void Failed(Trial*t,int i,Ptr<const Packet>p){Listen(t,i);}
void Interference(Trial*t,Ptr<const Packet>p,uint32_t n){++t->interfered;}
void HalfDuplex(Trial*t,Ptr<const Packet>p,uint32_t n){++t->halfduplex;}
void Under(Trial*t,Ptr<const Packet>p,uint32_t n){++t->under;}
Ptr<Packet> Frame(int bytes,int id){std::vector<uint8_t>data(bytes,0);data[0]=id;return Create<Packet>(data.data(),bytes);}
void Reply(Trial*t,int i){
 NS_ABORT_MSG_IF(t->ed[i]->GetState()!=EndDeviceLoraPhy::State::STANDBY,"reply while PHY busy");
 ++t->replies;int bytes=(t->longmask>>i&1)?27:20;
 t->ed[i]->Send(Frame(bytes,i),868100000+200000*(i%3),IQPolarity::UP,t->up,14);
}
void EdReceived(Trial*t,int i,Ptr<const Packet>p){
 uint8_t target=255;p->CopyData(&target,1);
 if(target==i)Simulator::Schedule(Seconds(.01),&Reply,t,i);
 else Listen(t,i);
}
void Listen(Trial*t,int i){
 NS_ABORT_MSG_IF(t->ed[i]->GetState()!=EndDeviceLoraPhy::State::STANDBY&&t->ed[i]->GetState()!=EndDeviceLoraPhy::State::SLEEP,"listen while PHY busy");
 t->ed[i]->ReceiveSingle(869525000,IQPolarity::DOWN,7,125000,255,MakeBoundCallback(&Listen,t,i));
}
void GwReceived(Trial*t,Ptr<const Packet>p){
 uint8_t i=255;p->CopyData(&i,1);if(i>=20)return;
 double now=Simulator::Now().GetSeconds()+.025;
 t->lastReply=std::max(t->lastReply,now);
 if(now<=t->H+1e-9)t->received|=1u<<i;else ++t->late;
}
void Query(Trial*t,int i){
 double now=Simulator::Now().GetSeconds();if(now>t->H)return;
 double hd=LoraPhy::GetTimeOnAir(17,t->down).GetSeconds();
 NS_ABORT_MSG_IF(now-t->last+1e-9<hd/t->duty,"downlink duty violated");
 NS_ABORT_MSG_IF(t->gw->IsTransmitting(),"gateway transmit overlap");
 t->last=now;++t->requests;t->gw->Send(Frame(17,i),869525000,IQPolarity::DOWN,t->down,14);
}
void Background(Trial*t,int i){
 NS_ABORT_MSG_IF(t->bg[i]->GetState()!=EndDeviceLoraPhy::State::STANDBY&&t->bg[i]->GetState()!=EndDeviceLoraPhy::State::SLEEP,"background overlap");
 ++t->bgSent;t->bg[i]->Send(Frame(20,255),868100000+200000*(i%3),IQPolarity::UP,t->up,14);
}
Ptr<ConstantPositionMobilityModel> Position(double x,double y){auto m=CreateObject<ConstantPositionMobilityModel>();m->SetPosition(Vector(x,y,0));return m;}
int main(int argc,char**argv){
 std::string input,output;CommandLine cmd;cmd.AddValue("input","Trial specification text",input);cmd.AddValue("output","Packet outcomes CSV",output);cmd.Parse(argc,argv);
 std::ifstream in(input);NS_ABORT_MSG_IF(!in,"missing trial input");std::ofstream out(output);NS_ABORT_MSG_IF(!out,"missing output");
 out<<"ID,ReceivedMask,Requests,Replies,LateReplies,BackgroundTransmissions,InterferenceEvents,HalfDuplexEvents,UnderSensitivityEvents,LastReplySeconds\n"<<std::setprecision(12);
 int id,background;uint32_t selected,longmask,geometry,random;double H,duty,radius;
 while(in>>id>>selected>>longmask>>H>>duty>>background>>radius>>geometry>>random){
  Trial t;t.mask=selected;t.longmask=longmask;t.H=H;t.duty=duty;t.down.crcEnabled=false;
  NS_ABORT_MSG_IF(std::abs(LoraPhy::GetTimeOnAir(17,t.down).GetSeconds()-.046336)>1e-10,"request ToA mismatch");
  NS_ABORT_MSG_IF(std::abs(LoraPhy::GetTimeOnAir(20,t.up).GetSeconds()-.056576)>1e-10,"short reply ToA mismatch");
  NS_ABORT_MSG_IF(std::abs(LoraPhy::GetTimeOnAir(27,t.up).GetSeconds()-.066816)>1e-10,"long reply ToA mismatch");
  auto loss=CreateObject<LogDistancePropagationLossModel>();loss->SetPathLossExponent(3.76);loss->SetReference(1,7.7);
  t.channel=CreateObject<LoraChannel>(loss,CreateObject<ConstantSpeedPropagationDelayModel>());
  t.gw=CreateObject<SimpleGatewayLoraPhy>();t.gw->SetMobility(Position(0,0));t.gw->SetChannel(t.channel);t.channel->Add(t.gw);
  for(int i=0;i<3;++i)t.gw->AddFrequency(868100000+200000*i);
  for(int i=0;i<8;++i)t.gw->AddReceptionPath();
  t.gw->SetReceiveOkCallback(MakeBoundCallback(&GwReceived,&t));
  t.gw->TraceConnectWithoutContext("LostPacketBecauseInterference",MakeBoundCallback(&Interference,&t));
  t.gw->TraceConnectWithoutContext("NoReceptionBecauseTransmitting",MakeBoundCallback(&HalfDuplex,&t));
  t.gw->TraceConnectWithoutContext("LostPacketBecauseUnderSensitivity",MakeBoundCallback(&Under,&t));
  std::mt19937 gen(geometry),rng(random);std::uniform_real_distribution<double> U(0,1);
  for(int i=0;i<20+background;++i){
   auto phy=CreateObject<SimpleEndDeviceLoraPhy>();double r=250+(radius-250)*std::sqrt(U(gen)),a=6.283185307179586*U(gen);
   phy->SetMobility(Position(r*std::cos(a),r*std::sin(a)));phy->SetChannel(t.channel);
   // Background transmitters are not receive targets; omit them from channel fanout.
   if(i<20){
    t.ed.push_back(phy);t.channel->Add(phy);
    phy->SetReceiveOkCallback(MakeBoundCallback(&EdReceived,&t,i));
    phy->SetReceiveFailedCallback(MakeBoundCallback(&Failed,&t,i));
    phy->SetTxFinishedCallback(MakeBoundCallback(&TxDone,&t,i));Listen(&t,i);
   }else{
    t.bg.push_back(phy);int j=i-20;double start=6*U(rng);
    // <=0.943% uplink duty per background device; fixed 6-s period.
    for(double at=start;at<H+.3;at+=6)Simulator::Schedule(Seconds(at),&Background,&t,j);
   }
  }
  double ready=.025,next=.025;
  for(int i=0;i<20;++i)if(selected>>i&1){
   double start=std::max(ready,next),reply=(longmask>>i&1)?.066816:.056576;
   Simulator::Schedule(Seconds(start),&Query,&t,i);
   ready=start+.046336+.01+reply;next=start+.046336/duty;
  }
  Simulator::Stop(Seconds(H+.3));Simulator::Run();Simulator::Destroy();
  NS_ABORT_MSG_IF(t.received&~selected,"unqueried resource received");
  out<<id<<','<<t.received<<','<<t.requests<<','<<t.replies<<','<<t.late<<','<<t.bgSent<<','<<t.interfered<<','<<t.halfduplex<<','<<t.under<<','<<t.lastReply<<'\n';
  for(auto p:t.ed)t.channel->Remove(p);t.channel->Remove(t.gw);
  // Break channel->PHY->channel ownership cycles between independent trials.
  for(auto p:t.ed)p->SetChannel(nullptr);for(auto p:t.bg)p->SetChannel(nullptr);t.gw->SetChannel(nullptr);
 }
 return 0;
}
