#include <generated/csr.h>
#include <generated/mem.h>
#if (defined CSR_SPIFLASH_BASE && defined SPIFLASH_PAGE_SIZE)
#include "flash.h"

#include <stdio.h>
#include <limits.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <uart.h>
#include <time.h>
#include <console.h>
#include <spiflash.h>
#include <crc.h>
#include <system.h>
#include "ci.h"

#include <modem.h>
#include <serial.h>

#define test_size 1024

static unsigned char bitbang_buffer[128*1024];
static unsigned char bus_buffer[128*1024];
static unsigned char xmodem_buffer[1029];
static unsigned char sector_buf_pre[SPIFLASH_SECTOR_SIZE];
static unsigned char sector_buf_post[SPIFLASH_SECTOR_SIZE];

typedef struct flash_writer {
	unsigned char * buf;
	size_t inlen;
	size_t bufpos;
	size_t buflen;
} flash_writer_t;

int write_to_buf(const char * buf, const int buf_size, const int eof, void * const chan_state);
static void write_to_flash_arb(unsigned int addr, unsigned int len, unsigned char * prepend_buf, unsigned char * append_buf);

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

	unsigned int buf_w[512];
	unsigned int buf_r[512];

	flashbase = (unsigned int *)FLASH_BOOT_ADDRESS;
	length = *flashbase++;
	free_start = flashbase + length;
	free_space = (unsigned int *)(SPIFLASH_BASE + SPIFLASH_SIZE) - free_start;

	printf("Free space begins at %X, size %d bytes.\n", free_start, free_space);
	mr((unsigned int) free_start, 512);

	for(i = 0; i < 512; i++) {
		buf_w[i] = (unsigned int) ( (i << 8) | i );
	}

	printf("Read using memory bus 1.\n");
	write_to_flash((unsigned int) free_start, (unsigned char *) buf_w, 512);
	flush_cpu_dcache();
	mr((unsigned int) free_start, 512);

	printf("Read using bitbang test.\n");
	read_from_flash((unsigned int) free_start, (unsigned char *) buf_r, 512);
	mr((unsigned int) &buf_r[0], 512); // &buf_r[0]: Collapse to ptr to first element.

	printf("Read using memory bus 2.\n");
	flush_cpu_dcache();
	mr((unsigned int) free_start, 512);

	erase_flash_sector((unsigned int) free_start);
}


// XMODEM:
// 10 tries to receive first char of packet- 10 seconds each
// First char of first packet special- either send NAK or C (for CRC)


// 1 second timeout for each recv'd char otherwise.

// XMODEM helpers


int write_to_buf(const char * buf, const int buf_size, const int eof, void * const chan_state) {
	flash_writer_t * writer = chan_state;

	int space_left = writer->buflen - writer->bufpos;

	int size_sent = space_left < buf_size ? space_left : buf_size;
	memcpy(writer->buf + writer->bufpos, buf, size_sent);

	writer->bufpos += size_sent;
	return size_sent;
}

int write_xmodem(unsigned long addr, unsigned long len, unsigned long crc) {
	flash_writer_t writer = { bitbang_buffer, len, 0, sizeof(bitbang_buffer)/sizeof(bitbang_buffer[0]) };
	serial_handle_t uart;
	unsigned int calc_crc;

	printf("Phase 1: Receive file (Please start XMODEM transmission).\r\n");
	serial_init(0, 0, &uart);
	int rc = xmodem_rx(write_to_buf, xmodem_buffer, &writer, uart, XMODEM_1K);
	serial_close(&uart);

	if(rc != MODEM_NO_ERRORS) {
		return -1;
	}

	// Do CRC check. Return if no match.
	printf("Phase 2: CRC check.\r\n");
	calc_crc = crc32((unsigned char *) bitbang_buffer, len);
	if(crc != calc_crc) {
		printf("CRC failed (expected %08x, got %08x)\n", crc, calc_crc);
		return -1;
	}

	write_to_flash_arb(addr, len, sector_buf_pre, sector_buf_post);

	memcpy(bus_buffer, (void *) addr, len);
	printf("Phase 5: Comparing memory bus to received data.\r\n");
	for(unsigned int count = 0; count < len; count++) {
		if(bus_buffer[count] != bitbang_buffer[count]) {
			printf("Comparison failed at offset %X\r\n", count);
			mr((unsigned int) &bus_buffer[count], 512);
			mr((unsigned int) &bitbang_buffer[count], 512);
			return -2;
		}
	}

	/* Phase 6 comparison. */
	memset(bitbang_buffer, '\0', len);
	printf("Phase 6: Comparing memory bus to bitbang reads.\r\n");
	read_from_flash(addr, (unsigned char *) bitbang_buffer, len);
	for(unsigned int count = 0; count < len; count++) {
		if(bus_buffer[count] != bitbang_buffer[count]) {
			printf("Comparison failed at offset %X\r\n", count);
			mr((unsigned int) &bus_buffer[count], 512);
			mr((unsigned int) &bitbang_buffer[count], 512);
			return -2;
		}
	}

	flush_cpu_dcache();
	mr(addr, 512);

	return 0;
}

int write_sfl(unsigned long addr, unsigned long len, unsigned long crc) {
	return 0;
}

static void write_to_flash_arb(unsigned int addr, unsigned int len, unsigned char * prepend_buf, unsigned char * append_buf) {
	printf("Phase 3: Erase flash region.\r\n");
	/* All end ptrs are "one past the last byte used for data of the
	previous start ptr". */
	unsigned int erase_addr = addr;
	unsigned int erase_end = erase_addr + len;
	unsigned int sector_start = erase_addr & ~(SPIFLASH_SECTOR_SIZE - 1);
	unsigned int sector_end = (erase_end & ~(SPIFLASH_SECTOR_SIZE - 1)) + SPIFLASH_SECTOR_SIZE;
	unsigned int prepend_len = erase_addr - sector_start;
	unsigned int append_len = sector_end - erase_end;

	memcpy(prepend_buf, (void *) sector_start, prepend_len);
	memcpy(append_buf, (void *) erase_end, append_len);
	erase_flash_sector(sector_start);
	printf("Write leading data.\r\n");
	write_to_flash(sector_start, prepend_buf, prepend_len);
	flush_cpu_dcache();

	unsigned int middle_sectors = sector_start + SPIFLASH_SECTOR_SIZE;

	while(middle_sectors < sector_end) {
		erase_flash_sector(middle_sectors);
		middle_sectors += SPIFLASH_SECTOR_SIZE;
	}

	printf("Write trailing data.\r\n");
	write_to_flash(erase_end, append_buf, append_len);
	flush_cpu_dcache();

	printf("Phase 4: Writing new data to flash.\r\n");
	write_to_flash(addr, (unsigned char *) bitbang_buffer, len);
	flush_cpu_dcache();
}




#endif
