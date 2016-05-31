#include <stdio.h>
#include <stdlib.h>

#include <generated/csr.h>
#include <generated/mem.h>
#include <hw/flags.h>
#include <system.h>
#include <time.h>

#define HDMI_IN0_FRAMEBUFFERS_BASE 0x00000000
#define HDMI_IN1_FRAMEBUFFERS_BASE 0x01000000
#define PATTERN_FRAMEBUFFER_BASE 0x02000000

#define YCBCR422_RED    0x544cff4c

void heartbeat(int h_active, int m_active)
{
	int i;
	flush_l2_cache();
	volatile unsigned int *framebuffer = (unsigned int *)(MAIN_RAM_BASE + HDMI_IN0_FRAMEBUFFERS_BASE);
	// FIX ME : Add correct address here

	int x, y;
	int mask[h_active][m_active]

	for (y=0; y<m_active; y++){
		for(x=0; x<h_active; x++){
			if( (y>(m_active - 4)) && (x>(h_active - 4)) ) 
				mask[x][y] = 1;
		}
	}


	for (y=0; y<m_active; y++){
		for (x=0; x<h_active; x++){

			i = y*h_active/2 + x/2;
			if(mask[x][y]==1){
				framebuffer[i] = YCBCR422_RED;
			}


		}
	}


}