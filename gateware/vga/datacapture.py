from migen.fhdl.std import *
from migen.bank.description import *


class DataCapture(Module, AutoCSR):

    """
    Migen module for capturing VGA data from AD9984A on VGA expansion board.

    `__init__` args:
        pads : vga pads from atlys platform

    output signals:
        r,g, b : each 8-bit wide signals for 3 color components of every pixel
        vsync  : vsync signal. Generally used to sof signal.
        de     : data enable signal. Asserted means visible/active region is being
                 captured at that moment
        valid  : data is valid. This should go high when AD9984A has been properly
                 initialized.

    clock domains:
        pix : all synchronous code in this module work on `pix` clock domain.
              No need to use RenameClockDomain

    Working: This module runs two counters, `counterX` and `counterY`. `counterX` is reset at
             the rising edge of HSYNC signal from AD9984A, and then is counted up at every
             rising edge of pixel clock. `counterY` is reset at rising edge of VSYNC signal
             and is counted up at every HSYNC occurrence. `de` signal is asserted whenever
             data captured is from visible region. VGA timing constants decide visible region.

    TODO:
        1. Make the timing values, which are currently constants, to configurable via
           CSRs.
        2. `valid` signal should be proper. Currently it just driven high always.
           But when support for configurable resolutions is added, we should wait for
           AD9984A IC's PLL to get locked and initialization to finish properly before
           driving this signal high.

    """

    def __init__(self, pads):

        self.counterX = Signal(16)
        self.counterY = Signal(16)

        self.r = Signal(8)
        self.g = Signal(8)
        self.b = Signal(8)
        self.de = Signal()
        self.vsync = Signal()
        self.hsync = Signal()
        self.valid = Signal()

        hActive = Signal()
        vActive = Signal()

        vsout = Signal()
        self.comb += vsout.eq(pads.vsout)
        vsout_r = Signal()
        vsout_rising_edge = Signal()
        self.comb += vsout_rising_edge.eq(vsout & ~vsout_r)
        self.sync.pix += vsout_r.eq(vsout)

        hsout = Signal()
        self.comb += hsout.eq(pads.hsout)
        hsout_r = Signal()
        hsout_rising_edge = Signal()
        self.comb += hsout_rising_edge.eq(hsout & ~hsout_r)
        self.sync.pix += hsout_r.eq(hsout)

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        # Interchange Red and Blue channels due to PCB issue
        # and instead of 0:8 we have to take 2:10 that is higher bits
        self.comb += [
            r.eq(pads.blue[2:]),
            g.eq(pads.green[2:]),
            b.eq(pads.red[2:]),
            self.vsync.eq(vsout),
            self.hsync.eq(hsout),
        ]

        self.sync.pix += [
            self.r.eq(r),
            self.g.eq(g),
            self.b.eq(b),

            self.counterX.eq(self.counterX + 1),

            If(hsout_rising_edge,
                self.counterX.eq(0),
                self.counterY.eq(self.counterY + 1)
            ),

            If(vsout_rising_edge,
               self.counterY.eq(0),
            ),

            # TODO: Make the timing values below as configurable by adding
            # CSRs

            #  VGA Scan Timing Values used below for 1024x768@60Hz
            #   Source: http://hamsterworks.co.nz/mediawiki/index.php/VGA_timings
            #
            #   Horizontal Scan:
            #       Hsync: 136; HBackPorch: 160, HActive: 1024
            #
            #   Vertical Scan:
            #       Vsync: 6; VBackPorch: 29; VActive: 768
            #
            If((136+160 < self.counterX) & (self.counterX <= 136+160+1024),
                hActive.eq(1)
            ).Else(
                hActive.eq(0)
            ),

            If((6+29 < self.counterY) & (self.counterY <= 6+29+768),
                vActive.eq(1)
            ).Else(
                vActive.eq(0)
            ),
        ]

        # FIXME : valid signal should be proper
        self.comb += [
            self.valid.eq(1),
            self.de.eq(vActive & hActive),
        ]
