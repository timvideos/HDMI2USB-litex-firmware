#include <generated/csr.h>
#include <generated/mem.h>
#ifdef SPIFLASH_PAGE_SIZE
#include "flash.h"

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <console.h>
#include <spiflash.h>
#include <system.h>
#include "ci.h"


#define test_size 1024


#define NUMBER_OF_BYTES_ON_A_LINE 16
static void dump_bytes(unsigned int *ptr, int count, unsigned addr)
{
	char *data = (char *)ptr;
	int line_bytes = 0, i = 0;

	putsnonl("Memory dump:");
	while(count > 0){
		line_bytes =
			(count > NUMBER_OF_BYTES_ON_A_LINE)?
				NUMBER_OF_BYTES_ON_A_LINE : count;

		printf("\n0x%08x  ", addr);
		for(i=0;i<line_bytes;i++)
			printf("%02x ", *(unsigned char *)(data+i));

		for(;i<NUMBER_OF_BYTES_ON_A_LINE;i++)
			printf("   ");

		printf(" ");

		for(i=0;i<line_bytes;i++) {
			if((*(data+i) < 0x20) || (*(data+i) > 0x7e))
				printf(".");
			else
				printf("%c", *(data+i));
		}

		for(;i<NUMBER_OF_BYTES_ON_A_LINE;i++)
			printf(" ");

		data += (char)line_bytes;
		count -= line_bytes;
		addr += line_bytes;
	}
	printf("\n");
}

static void mr(unsigned int addr, unsigned int length)
{
	dump_bytes((unsigned int *) addr, length, (unsigned)addr);
}

void flash_test(void) {
	printf("flash_test\n");
	mr(0x20000000, test_size);
}

void bitbang_test(void) {
	unsigned int *flashbase;
	unsigned int length;
	unsigned int *free_start;
	unsigned int free_space;
	int i = 0;

	unsigned int buf[512];

	flashbase = (unsigned int *)FLASH_BOOT_ADDRESS;
	length = *flashbase++;
	free_start = flashbase + length;
	free_space = (unsigned int *)(SPIFLASH_BASE + SPIFLASH_SIZE) - free_start;

	printf("Free space begins at %X, size %d bytes.\n", free_start, free_space);
	mr((unsigned int) free_start, 512);

	for(i = 0; i < 512; i++) {
		buf[i] = ~(*(free_start + i));
	}

	write_to_flash((unsigned int) free_start, (unsigned char *) buf, 512);
	flush_cpu_dcache();
	mr((unsigned int) free_start, 512);
	erase_flash_sector((unsigned int) free_start);
}

#endif
