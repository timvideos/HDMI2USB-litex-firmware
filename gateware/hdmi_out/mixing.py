from migen.fhdl.std import *
from migen.flow.network import *

from gateware.csc.ycbcr2rgb import YCbCr2RGB
from gateware.csc.ycbcr422to444 import YCbCr422to444
from gateware.csc.ymodulator import YModulator
from gateware.csc.rgb2rgb16f import RGB2RGB16f
from gateware.csc.rgb16f2rgb import RGB16f2RGB
from gateware.float_arithmetic.floatmult import FloatMultRGB
from gateware.float_arithmetic.floatadd import FloatAddRGB

class MixerBlock(Module):
    def __init__(self, pixel_layout_c, pixel_layout, pack_factor):
        self.pixel_in_wide = Sink(pixel_layout_c)
        self.pixel_out = Source(pixel_layout)
        self.busy = Signal()

        ###

        self.comb += [
            self.busy.eq(0),
            self.pixel.stb.eq(self.pixel_wide.stb),
            self.pixel_wide.ack.eq(self.pixel.ack & self.pixel.stb)
        ]

        for i in range(pack_factor):

            chroma_upsampler = YCbCr422to444()
            self.submodules += RenameClockDomains(chroma_upsampler, "pix")
            self.comb += [
    #          chroma_upsampler.sink.stb.eq(fifo.pix_de),
    #          chroma_upsampler.sink.sop.eq(fifo.pix_de & ~de_r),
    #          chroma_upsampler.sink.y.eq(fifo.pix_y),
    #          chroma_upsampler.sink.cb_cr.eq(fifo.pix_cb_cr)
            ]

            ycbcr2rgb = YCbCr2RGB()
            self.submodules += RenameClockDomains(ycbcr2rgb, "pix")
            self.comb += [
                Record.connect(chroma_upsampler.source, ycbcr2rgb.sink),
                ycbcr2rgb.source.ack.eq(1)
            ]


        for i in range(pack_factor):
            self.comb += [getattr(self.pixel,"p"+str(i)).y.eq(getattr(self.pixel_wide.n0,"p"+str(i)).y)]
            self.comb += [getattr(self.pixel,"p"+str(i)).cb_cr.eq(getattr(self.pixel_wide.n0,"p"+str(i)).cb_cr)]

