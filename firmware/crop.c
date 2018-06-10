
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

void crop_service(fb_ptrdiff_t fb_offset,int top,int bottom,int left,int right)
{
	static int last_event;
	static int counter;
	static bool color_v;

	if (crop_stat==1) {
		crop_fill(color_v, fb_offset,top,bottom,left,right);

	}
}

void crop_fill(bool color_v, fb_ptrdiff_t fb_offset,int top,int bottom,int left,int right)
{
	int addr, i, j;
	unsigned int color;
	unsigned int *framebuffer = fb_ptrdiff_to_main_ram(fb_offset);

//Bottom clipping
	
	addr = 0 + (processor_h_active/2)*(processor_v_active-bottom);// + (processor_h_active/2) - right;
	for (i=0; i<processor_h_active/2; i++){
		for (j=0; j<processor_v_active - bottom; j++){
			framebuffer[addr+i+(processor_h_active/2)*j] = YCBCR422_BLACK;
		}
	}
//top clipping
        addr = 0;// + (processor_h_active/2);// + (processor_h_active/2) - right;
        for (i=0; i<processor_h_active/2; i++){
                for (j=0; j<top; j++){
                        framebuffer[addr+i+(processor_h_active/2)*j] = YCBCR422_BLACK;
                }
        }
//right clipping
	addr = 0 + (processor_h_active/2)*top + (processor_h_active/2) - right;
        for (i=0; i<right; i++)
	{
             for (j=0; j<processor_v_active - bottom; j++)
	    {
                framebuffer[addr+i+(processor_h_active/2)*j] = YCBCR422_BLACK;
            }
        }

//left clipping
	addr = 0 + (processor_h_active/2)*top;
        for (i=0; i<left; i++){
                for (j=0; j<processor_v_active-bottom; j++){
                        framebuffer[addr+i+(processor_h_active/2)*j] = YCBCR422_BLACK;
                }
        }


}
