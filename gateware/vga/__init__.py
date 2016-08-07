from migen.fhdl.std import *
from migen.bank.description import *

from gateware.hdmi_in.dma import DMA
from gateware.vga.analysis import FrameExtraction
from gateware.vga.datacapture import DataCapture


class VGAIn(Module, AutoCSR):

    def __init__(self, pads, lasmim, n_dma_slots=2, fifo_depth=512):

        self.clock_domains.cd_pix = ClockDomain()
        self.comb += [
          self.cd_pix.clk.eq(pads.datack),
          self.cd_pix.rst.eq(ResetSignal())  # XXX FIXME
        ]
        self.cap = DataCapture(pads)
        self.submodules += self.cap

        self.submodules.frame = FrameExtraction(lasmim.dw, fifo_depth)

        self.comb += [
            self.frame.valid_i.eq(self.cap.valid),
            self.frame.de.eq(self.cap.de),
            self.frame.vsync.eq(self.cap.vsync),
            self.frame.r.eq(self.cap.r),
            self.frame.g.eq(self.cap.g),
            self.frame.b.eq(self.cap.b)
        ]

        self.submodules.dma = DMA(lasmim, n_dma_slots)
        self.comb += self.frame.frame.connect(self.dma.frame)
        self.ev = self.dma.ev

    autocsr_exclude = {"ev"}
