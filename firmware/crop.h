#ifndef __CROP_H
#define __CROP_H

#include <stdbool.h>
#include "framebuffer.h"

void crop_status(bool val);
void crop_service(fb_ptrdiff_t fb_offset,int top,int bottom,int left,int right) ;
void crop_fill(bool color_v, fb_ptrdiff_t fb_offset,int top,int bottom,int left,int right);

#endif /* __HEARTBEAT_H */
