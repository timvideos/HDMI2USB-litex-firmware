include ../include/generated/variables.mak
include $(SOC_DIRECTORY)/software/common.mak

VPATH=$(MODEM_DIRECTORY)

include $(MODEM_DIRECTORY)/Makefile.mk

libmodem.a: build.ninja ninja-hack
	ninja -f $<

# meson doesn't understand vpath
REALSRCDIR=$(MODEM_DIRECTORY)/$(LIBMODEMDIR)

build.ninja: $(LIBMODEMDIR)/meson.build $(LIBMODEMDIR)/targets/hdmi2usb-$(CPU).txt
	meson.py . $(REALSRCDIR) -Db_staticpic=false -Dhdmi2usb_dir=$(BUILDINC_DIRECTORY)/../.. --cross-file=$(REALSRCDIR)/targets/hdmi2usb-$(CPU).txt

.PHONY: ninja-hack
