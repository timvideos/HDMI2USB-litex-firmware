#include <stdio.h>
#include <generated/csr.h>

#include "freq.h"

void freq_dump(void)
{
    printf("Frequency: %d Hz\n", freq_count_freq_out_read());
}
