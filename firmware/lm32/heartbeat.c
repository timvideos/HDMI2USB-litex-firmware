#include <stdio.h>
#include <stdlib.h>

#include <generated/csr.h>
#include <generated/mem.h>
#include <hw/flags.h>
#include <system.h>
#include <time.h>

#define HDMI_IN0_FRAMEBUFFERS_BASE 	0x01000000
#define HDMI_IN1_FRAMEBUFFERS_BASE 	0x02000000
#define PATTERN_FRAMEBUFFER_BASE 	0x03000000

#define YCBCR422_RED    0x544cff4c

void heartbeat(int h_active, int m_active, )
{
	int i;
	volatile unsigned int *framebuffer = (unsigned int *)(MAIN_RAM_BASE + HDMI_IN0_FRAMEBUFFERS_BASE);
	// FIX ME : Add correct address here

	int addr;
	int toggle;
	static int last_event;

	// A 4x4 pixel patch in right bottom


	addr = (h_active/2)*(m_active-4) + ( h_active/2 -2)

	for (i=0; i<8; i++){

	if(elapsed(&last_event, identifier_frequency_read()/1000)) {
		if(toggle==0) {
			framebuffer[addr] = YCBCR422_RED; 
			toggle = 1;
		}

		else toggle = 0;
	}


		if( i%2 == 1) addr = addr+(h/2) ;
		else addr = addr + 1;

	}

}