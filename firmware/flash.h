#ifndef __FLASH_H
#define __FLASH_H

void flash_test(void);
void bitbang_test(void);

#ifdef CSR_UART_BASE
int write_xmodem(unsigned long addr, unsigned long len);
int write_sfl(unsigned long addr, unsigned long len, unsigned long crc);
#endif

#endif /* __FLASH_H */
