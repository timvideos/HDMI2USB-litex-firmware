
#include <generated/csr.h>
#include <generated/mem.h>
#include <hw/flags.h>
#include <system.h>
#include <time.h>

#include "hdmi_in0.h"
#include "hdmi_in1.h"
#include "crop.h"
#include "processor.h"
#include "pattern.h"
#include "stdio_wrap.h"

static bool crop_stat = false;

void crop_status(bool val)
{
	crop_stat = val;
}

void crop_service(fb_ptrdiff_t fb_offset,int top)
{
	static int last_event;
	static int counter;
	static bool color_v;

	if (crop_stat==1) {
		crop_fill(color_v, fb_offset,top);
	}
}

void crop_fill(bool color_v, fb_ptrdiff_t fb_offset,int top)
{
	int addr1,addr2,addr3,addr4, i, j,k;
	unsigned int color;
	unsigned int *framebuffer = fb_ptrdiff_to_main_ram(fb_offset);

	addr1 = 0 + (processor_h_active/2)*(processor_v_active-top);
	addr2 = 0;
	addr3 = 0 + (processor_h_active/2)*top + (processor_h_active/2) - top;
	addr4 = 0 + (processor_h_active/2)*top;

	for (i=0; i<processor_h_active/2; i++)
	{
		for (j=0; j<processor_v_active - top; j++)
		{
			framebuffer[addr1+i+(processor_h_active/2)*j] = YCBCR422_BLACK;
		}
		for (k=0; k<top; k++)
		{
			framebuffer[addr2+i+(processor_h_active/2)*k] = YCBCR422_BLACK;
		}
	} /*Bottom clipping & top clipping*/

	for (i=0; i<top; i++)
	{
		for (j=0; j<processor_v_active - top; j++)
		{
			framebuffer[addr3+i+(processor_h_active/2)*j] = YCBCR422_BLACK;
		}
		for (k=0; k<processor_v_active-top; k++)
		{
			framebuffer[addr4+i+(processor_h_active/2)*k] = YCBCR422_BLACK;
		}

	} /*right clipping & left clipping*/
}
