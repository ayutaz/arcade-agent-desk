#include <stdint.h>
#include <string.h>
static int32_t stored,beeps,rects,io,in_size,out_size;
static uint8_t input[64],output[64];
void mock_reset(int32_t value){stored=value;beeps=rects=io=in_size=out_size=0;}
int32_t mock_generation(void){return stored;}
int32_t mock_beeps(void){return beeps;}
int32_t mock_rects(void){return rects;}
int32_t mock_io(void){return io;}
void mock_input(const uint8_t *p,int32_t n){memcpy(input,p,n);in_size=n;}
int32_t mock_output(uint8_t *p){int32_t n=out_size;memcpy(p,output,n);out_size=0;return n;}
void rect(int32_t x,int32_t y,int32_t w,int32_t h,int32_t color){
 (void)color;if(!x&&!y&&w==320&&h==240)rects=0;rects++;
}
int32_t state_read(int32_t slot,int32_t fallback){(void)slot;io++;return stored<0?fallback:stored;}
int32_t state_status(void){io++;return stored<0?-1:stored?1:0;}
int32_t state_write(int32_t slot,int32_t value){(void)slot;io++;if(stored<0)return -1;stored=value;return 1;}
int32_t network_receive(uint8_t *p,int32_t cap){io++;if(in_size>cap)return -1;int32_t n=in_size;memcpy(p,input,n);in_size=0;return n;}
int32_t network_send(const uint8_t *p,int32_t n){io++;memcpy(output,p,n);out_size=n;return 1;}
int32_t audio_tone(int32_t hz,int32_t ms){(void)hz;(void)ms;io++;beeps++;return 1;}
int32_t audio_state(void){io++;return 0;}
