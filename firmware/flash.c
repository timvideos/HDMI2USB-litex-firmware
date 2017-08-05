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
#include <system.h>
#include "ci.h"

#define test_size 1024

static char bitbang_buffer[128*1024];
static char bus_buffer[128*1024];
static char xmodem_buffer[1029];

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


#define SOH 1
#define STX 2
#define EOT 4
#define ACK 6
#define NAK 21
#define CAN 24

static inline unsigned short generate_crc(char * data, size_t size)
{
	const unsigned int crc_poly = 0x1021;
	unsigned int crc = 0x0000;

	for(unsigned int octet_count = 0; octet_count < size; octet_count++)
	{
		crc = (crc ^ (unsigned int) (data[octet_count] & (0xFF)) << 8);
		for(unsigned int bit_count = 1; bit_count <= 8; bit_count++)
		{
			if(crc & 0x8000)
			{
				crc = (crc << 1) ^ crc_poly;
			}
			else
			{
				crc <<= 1;
			}       
		}
	}
	return crc;
}


// Return:
// 0- Read was okay.
// 1- We timed out.
static int recv_with_timeout(unsigned int timeout, char * recvd) {
	// Software-based timeout for now while QEMU timer is broken.
	// 1/100th of clock frequency worked well for me.
	for(unsigned int i = 0; i < CONFIG_CLOCK_FREQUENCY/100; i++) {
		for(unsigned int j = 0; j < timeout; j++) {
			//printf("%d, %d", i, j);
			if(uart_read_nonblock()) {
				*recvd = uart_read();
				return 0;
			}	
		}
	}
	
	return -1;
}


// Clear UART buffer until timeout occurs.
static void purge_uart_buffer(void) {
	char dummy;
	while(recv_with_timeout(1, &dummy) == 0);
}


// Return
// 0- Recv okay
// -1- Transmitter timed out
// -2- Using 1k and checksum- This doesn't make sense.
// Full packet (including already filled start char) should be
// passed into this function.
static int recv_packet_with_timeout(char * packet, int using_crc, int using_1k) {
	int bytes_total = 3; // 2 bytes for block number and ones-compl
	
	if(using_crc) {
		bytes_total += 2;
	} else {
		bytes_total += 1;
	} 
	
	if(using_1k) {
		if(using_crc) {
			return -2;
		} else {
			bytes_total += 1024;
		}
	} else {
		bytes_total += 128;
	}

	for(int i = 1; i < bytes_total; i++) {
		char xmit;
		
		if(recv_with_timeout(1, &xmit) == -1) {
			return -1;
		} else {
			packet[i] = xmit;	
		}
	}
	
	return 0;
}

// Return codes:
// 128 or 1024
// -1- Invalid config
static inline int payload_len(int using_crc, int using_1k) {
	if(using_1k) {
		if(using_crc) {
			return -1;
		} else {
			return 1024;
		}
	} else {
		return 128;
	}
}


// Return codes:
// 1- Previous block was resent- everything else okay.
// 0- All is okay
// -1- Invalid configuration
// -2- Block mismatch in header
// -3- Unexpected block
// -4- Bad CRC/Checksum
static inline int verify_packet(char * packet, unsigned char expected_block, int using_crc, int using_1k) {
	int rc = 0;
	
	if(packet[1] == (expected_block - 1)) {
		rc = 1;
	} else if(packet[1] == expected_block) {
		rc = 0; // Do nothing
	} else {
		return -3;
	}

	if(!(packet[1] == !packet[2])) {
		return -2;
	}

	if(using_crc) {
		if(!(generate_crc(&packet[3], payload_len(using_crc, using_1k) == 0))) {
			return -4;
		}
	} else {
		return -4; // Not implemented yet
	}
	
	return rc;
}


// Abbreviated xmodem.
int write_xmodem(unsigned long addr, unsigned long len) {
	int using_1k = 0;
	int using_crc = 1;
	int initial_retries = 0;
	unsigned int data_offset = 0;
	unsigned char expected_block = 1;
	
	// Initial handshake
	for(initial_retries = 0; initial_retries < 10; initial_retries++) {
		char first;
		char send = using_crc ? 'C' : NAK;
		uart_write(send);
		int res = recv_with_timeout(10, &first);

		if(res == 0) {
			switch(first) {
				case SOH:
					xmodem_buffer[0] = first;
					goto initial_handshake_over;
					break;
				case STX:
					xmodem_buffer[0] = first;
					using_1k = 1;
					goto initial_handshake_over;
					break;
				default:
					// Unexpected/invalid char.
					purge_uart_buffer();
					break;
			}
		}
		
		// Switch to checksum mode after three timeouts.
		if(initial_retries == 3) {
			using_crc = 0; // Only set here. 
		}
	}
	
initial_handshake_over:
	if(initial_retries >= 10) {
		return -1;
	}
	
	int initial_handshake_occurred = 1;
	int done = 0;
	int num_errors = 0;
	char send_code;
	while(!done) {
		// Skip this the first time around. For control flow purposes
		// It makes sense to keep it at top of while loop.	
		if(!initial_handshake_occurred) {
			int res;
			char first;
			
			if(num_errors >= 10) {
				send_code = CAN;
			}
			
			// Subsequent handshakes
			if(send_code == NAK)
			{
				purge_uart_buffer();
			}

			uart_write(send_code);
			if(send_code == CAN) {
				return -1;
			} else {
				res = recv_with_timeout(10, &first);
			}

			if(res == 0) {
				switch(first) {
					case SOH:
						xmodem_buffer[0] = first;
						break;
					case STX:
						xmodem_buffer[0] = first;
						using_1k = 1;
						break;
					case EOT:
						done = 1;
						continue;
					default:
						// Unexpected/invalid char.
						send_code = NAK;
						num_errors++;
						continue;
				}
			} else {
				send_code = NAK;
				num_errors++;
				continue;
			}
		}
		
		if(initial_handshake_occurred) {
			initial_handshake_occurred = 0;
		}
		
		
		// Subsequent receives
		int recv_rc = recv_packet_with_timeout(xmodem_buffer, using_crc, using_1k);
		switch(recv_rc) {
			case 0:
				break;
			case -2:
				send_code = CAN;
				num_errors++;
				continue;
			case -1:
			default:
				send_code = NAK;
				num_errors++;
				continue;
		}
		
		int ver_rc = verify_packet(xmodem_buffer, expected_block, using_crc, using_1k);
		switch(ver_rc) {
			case 0:
				// Assuming !using_crc && using_1k is impossible.
				{
					int len = payload_len(using_crc, using_1k);
					memcpy(bus_buffer + data_offset + len, xmodem_buffer + 3, len);
					data_offset += len;
				}
				send_code = ACK;
				expected_block++;
				break;
			case 1: // Last block was resent. Nothing to do.
				send_code = ACK;
				break;
			case -1:
			case -3:
				send_code = CAN;
				num_errors++;
				continue;
			case -2:
			case -4:
			default:
				send_code = NAK;
				num_errors++;
				continue;
		}
		
		// Every time we successfully send a packet, reset error count.
		num_errors = 0;
	}
	
	return 0;
}




int write_sfl(unsigned long addr, unsigned long len, unsigned long crc) {
	return 0;
}

#endif
