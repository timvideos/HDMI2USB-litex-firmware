#include <generated/csr.h>
#include <generated/mem.h>
#include <hw/flags.h>
#include <system.h>
#include <time.h>
#include <stdbool.h>

#include "processor.h"
#include "hdmi_in0.h"
#include "hdmi_in1.h"
#include "pattern.h"
#include "mix.h"

static const unsigned int mult_bar[20] = {
	0 	  ,
	10854 ,
	11878 ,
	12493 ,
	12902 ,
	13312 ,
	13517 ,
	13722 ,
	13926 ,
	14131 ,
	14336 ,
	14438 ,
	14541 ,
	14643 ,
	14746 ,
	14848 ,
	14950 ,
	15053 ,
	15155 ,
	15258 
};

#define FILL_RATE 20 			// In Hertz, double the standard frame rate

unsigned int mult_factor_0 = 0;
unsigned int mult_factor_1 = 15360 ;

void mult_service(void)
{
	static int last_event;
	static int counter;

//	if (mix_status) {
		if(elapsed(&last_event, identifier_frequency_read()/FILL_RATE)) {
			counter = counter+1;
			mult_factor_0 = mult_bar[counter];
			mult_factor_1 = mult_bar[20-1-counter];

			if(counter >= (FILL_RATE-1)) {
				counter = 0;
			}
		}
//	}

/*	hdmi_out0_driver_mult_r_write(mult_factor_0);
	hdmi_out0_driver_mult_g_write(mult_factor_0);
	hdmi_out0_driver_mult_b_write(mult_factor_0);

	hdmi_out1_driver_mult_r_write(mult_factor_1);
	hdmi_out1_driver_mult_g_write(mult_factor_1);
	hdmi_out1_driver_mult_b_write(mult_factor_1);
*/
}
