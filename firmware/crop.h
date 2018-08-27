#ifndef __CROP_H
#define __CROP_H

#include <stdbool.h>
#include "framebuffer.h"

void crop_status(bool val);
void crop_service(fb_ptrdiff_t fb_offset,int top) ;
void crop_fill(bool color_v, fb_ptrdiff_t fb_offset,int top);

