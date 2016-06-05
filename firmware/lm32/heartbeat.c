
#include <generated/csr.h>
#include <generated/mem.h>
#include <hw/flags.h>
#include <system.h>
#include <time.h>

void heartbeat(int h_active, int m_active )
{
	int i;
	volatile unsigned int *framebuffer = (unsigned int *)(MAIN_RAM_BASE + HDMI_IN0_FRAMEBUFFERS_BASE);
	// FIX ME : Add correct address here
	
	int addr;
	int toggle;
	static int last_event;
	
	/*
	For loops over 8 memory locations, which correspond to 16 (4x4) pixels at right bottoom corner
	Each memory location corresponds to 2 horizoantal pixels
	Variable addr corresponds to the address of the first pixel required to be changed
	*/

	addr = (h_active/2)*(m_active-4) + ( h_active/2 -2)
		
	for (i=0; i<8; i++){
		
		if(elapsed(&last_event, identifier_frequency_read()/1000)) {
			if(toggle==0) {
				framebuffer[addr] = YCBCR422_RED;
				toggle = 1;
			}
			else toggle = 0;
			}
		
		if( i%2 == 1) addr = addr + (h_active/2) ;
		else addr = addr + 1;
			
	}
	
}
