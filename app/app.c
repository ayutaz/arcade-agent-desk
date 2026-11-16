#include "lab_os.h"
#include "desk_key.h"
enum {WORK=1,DONE=2,FAIL=3,WAIT=4,CANCEL=5,LOST=6};
static uint32_t generation,sequence,selected,hello_age,persist_pending,seen[4],age[4],ttl[4],elapsed[4];
static uint8_t status[4],progress[4],incoming[64],outgoing[16];
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t get64(const uint8_t *p){return (uint64_t)get32(p)|(uint64_t)get32(p+4)<<32;}
static void put32(uint8_t *p,uint32_t x){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(x>>(8*i));}
static uint64_t rot(uint64_t x,unsigned n){return (x<<n)|(x>>(64-n));}
static void round64(uint64_t *v){
 v[0]+=v[1];v[1]=rot(v[1],13)^v[0];v[0]=rot(v[0],32);
 v[2]+=v[3];v[3]=rot(v[3],16)^v[2];v[0]+=v[3];v[3]=rot(v[3],21)^v[0];
 v[2]+=v[1];v[1]=rot(v[1],17)^v[2];v[2]=rot(v[2],32);
}
static uint64_t mac(const uint8_t *p,unsigned n){
 uint64_t k0=get64(desk_key),k1=get64(desk_key+8);
 uint64_t v[4]={0x736f6d6570736575ULL^k0,0x646f72616e646f6dULL^k1,0x6c7967656e657261ULL^k0,0x7465646279746573ULL^k1};
 unsigned i=0;for(;i+8<=n;i+=8){uint64_t m=get64(p+i);v[3]^=m;round64(v);round64(v);v[0]^=m;}
 uint64_t m=(uint64_t)n<<56;for(unsigned j=0;i<n;i++,j++)m|=(uint64_t)p[i]<<(8*j);
 v[3]^=m;round64(v);round64(v);v[0]^=m;v[2]^=255;
 for(i=0;i<4;i++)round64(v);return v[0]^v[1]^v[2]^v[3];
}
static int persist(void){
 int32_t result=state_write(0,(int32_t)generation);
 if(result<0){generation=0;persist_pending=0;return 0;}
 if(result==1)persist_pending=0;return result==1;
}
uint32_t sdk_abi(void){return LAB_ABI;}
void init(void){
 generation=sequence=hello_age=persist_pending=0;selected=0;
 for(unsigned i=0;i<4;i++){seen[i]=age[i]=elapsed[i]=0;ttl[i]=5000;status[i]=LOST;progress[i]=255;}
 int32_t prior=state_read(0,0),found=state_status();
 if(found>=0&&prior>=0&&prior<0x7fffffff){generation=(uint32_t)prior+1;persist_pending=1;persist();}
}
void shutdown(uint32_t reason){(void)reason;}
static int view_state(void){return !seen[selected]||age[selected]>=ttl[selected]?LOST:status[selected];}
int32_t debug_value(void){return view_state();}
int32_t debug_x(void){return (int32_t)selected+1;}
int32_t debug_y(void){return (int32_t)generation;}
int32_t debug_elapsed(void){return (int32_t)elapsed[selected];}
static int receive(int32_t n){
 if(n!=40||incoming[0]!='A'||incoming[1]!='D'||incoming[2]!='S'||incoming[3]!='1')return 0;
 if((mac(incoming,32)^get64(incoming+32))!=0)return 0;
 uint32_t gen=get32(incoming+4),seq=get32(incoming+8),task=get32(incoming+12),time=get32(incoming+16),life=get32(incoming+24);
 uint32_t state=incoming[20],percent=incoming[21],distance=seq-sequence;
 if(gen!=generation||!seq||task<1||task>4||state<1||state>5||(percent>100&&percent!=255)||
    incoming[22]||incoming[23]||get32(incoming+28)||life<1000||life>30000||
    (sequence&&(!distance||distance>=0x80000000u)))return 0;
 unsigned index=task-1;int changed=!seen[index]||status[index]!=state;
 unsigned any=seen[0]|seen[1]|seen[2]|seen[3];if(!any)selected=index;
 sequence=seq;seen[index]=1;age[index]=0;ttl[index]=life;elapsed[index]=time;status[index]=(uint8_t)state;progress[index]=(uint8_t)percent;
 return changed&&(state==DONE||state==FAIL||state==WAIT);
}
static void word(const char *text,int32_t x,int32_t y,int32_t color){
 /* Five-column, seven-row glyphs drawn as horizontal runs within the 128-rect budget. */
 const char *letters="WORKDNEFAILTSC";
 static const uint8_t glyph[14][7]={
 {17,17,17,21,21,21,10},{14,17,17,17,17,17,14},{30,17,17,30,20,18,17},
 {17,18,20,24,20,18,17},{30,17,17,17,17,17,30},{17,25,25,21,19,19,17},
 {31,16,16,30,16,16,31},{31,16,16,30,16,16,16},{14,17,17,31,17,17,17},
 {14,4,4,4,4,4,14},{16,16,16,16,16,16,31},{31,4,4,4,4,4,4},
 {15,16,16,14,1,1,30},{14,17,16,16,16,17,14}};
 for(unsigned c=0;text[c];c++){
  unsigned g=0;while(letters[g]&&letters[g]!=text[c])g++;
  if(!letters[g])continue;
  for(unsigned row=0;row<7;row++)for(unsigned col=0;col<5;){
   if(!(glyph[g][row]&(16u>>col))){col++;continue;}
   unsigned start=col;while(col<5&&(glyph[g][row]&(16u>>col)))col++;
   rect(x+(int32_t)(c*6+start)*6,y+(int32_t)row*6,(int32_t)(col-start)*6,6,color);
  }
 }
}
int32_t tick(uint32_t held,uint32_t pressed,uint32_t released,uint32_t dt){
 (void)held;(void)released;if(pressed&BACK)return 1;
 for(unsigned i=0;i<4;i++)age[i]=age[i]>60000-dt?60000:age[i]+dt;
 if(pressed&(RIGHT|LEFT)){
  for(unsigned n=1;n<5;n++){unsigned i=(selected+(pressed&RIGHT?n:4-n))%4;if(seen[i]){selected=i;break;}}
 }
 int notify=0;
 if(generation){
  if(persist_pending)persist();
  else {
   int32_t n=network_receive(incoming,64);if(n>0)notify=receive(n);
   hello_age+=dt;
   if(hello_age>=1000){
    outgoing[0]='A';outgoing[1]='D';outgoing[2]='H';outgoing[3]='1';put32(outgoing+4,generation);
    uint64_t tag=mac(outgoing,8);for(unsigned i=0;i<8;i++)outgoing[i+8]=(uint8_t)(tag>>(8*i));
    if(network_send(outgoing,16)==1)hello_age=0;
   }
  }
 }
 if(notify&&audio_state()==0)audio_tone(status[selected]==FAIL?440:880,120);
 int state=view_state();int32_t color=state==DONE?2016:state==FAIL?63488:state==WORK?2047:state==WAIT?65504:33808;
 rect(0,0,320,240,0);
 for(unsigned i=0;i<4;i++)rect(20+(int32_t)i*72,20,62,8,i==selected?65535:seen[i]?color:4226);
 const char *text=state==WORK?"WORK":state==DONE?"DONE":state==FAIL?"FAIL":state==WAIT?"WAIT":state==CANCEL?"CANC":"LOST";
 word(text,88,92,color);
 rect(24,172,272,12,4226);
 if(state!=LOST&&progress[selected]<=100&&progress[selected])rect(24,172,(int32_t)(progress[selected]*272/100),12,color);
 for(unsigned i=0;i<4;i++)rect(137+(int32_t)i*12,205,6,6,i<=selected?color:4226);
 return 0;
}
