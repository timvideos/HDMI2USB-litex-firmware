`libmodem` currently uses a separate build system from the rest of HDMI2USB.

The purpose of this directory is to provide a make wrapper around `libmodem`
that Litex picks up as a dependency.

When building `libmodem` as a dependency of HDMI2USB, there are four directories
used (relative to `$HDMI2USB_ROOT` and for a given `$TARGET`):

* `$HDMI2USB_ROOT/firmware/modem`: This directory, where Makefiles live.
* `$HDMI2USB_ROOT/third_party/libmodem`: `libmodem` source code.
* `$HDMI2USB_ROOT/build/$TARGET/third_party/libmodem`: Meson output/`build.ninja` are generated here.
* `$HDMI2USB_ROOT/build/$TARGET/software/modem`: Object files and `libmodem.a` are generated here.
