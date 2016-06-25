# rgb16f2rgb

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.flow.actor import *

from gateware.csc.common import *

datapath_latency = 2

@DecorateModule(InsertCE)
class PIXF2PIXDatapath(Module):
    def __init__(self, pixf_w, pix_w):
        self.sink = sink = Record(pixf_layout(pixf_w))
        self.source = source = Record(pix_layout(pix_w))

        # # #

        # delay pixff signals
        pixf_delayed = [sink]
        for i in range(datapath_latency):
            pixf_n = Record(pixf_layout(pixf_w))
            self.sync += getattr(pixf_n, "pixf").eq(getattr(pixf_delayed[-1], "pixf"))
            pixf_delayed.append(pixf_n)


        # Hardware implementation:
        # Float is defines in the range [0-1] (higher precision)
        # Uint8 is defined in the range [0-255]

        # stage 1
        # Unpack
        # Correct exponent offset for shifting later

        r_frac = Signal(11)
        r_exp = Signal(5)
        r_exp_offset = Signal(5)
		
        self.sync += [
        
            r_exp_offset.eq(15 - sink.pixf[10:15] -1),    
            r_frac[:10].eq(sink.pixf[:10]),
            r_frac[10].eq(1),
        ]

        # stage 2
        # Right shift r_frac by r_exp_offset
        # r_exp_offset = 1
        # Most significant 8 bits of r_frac assigned to int8 r

        self.sync += [
            source.pix.eq( (r_frac >> r_exp_offset)[3:]),
        ]


class RGB16f2RGB(PipelinedActor, Module):
    def __init__(self, rgb16f_w=16, rgb_w=8, coef_w=8):
        self.sink = sink = Sink(EndpointDescription(rgb16f_layout(rgb16f_w), packetized=True))
        self.source = source = Source(EndpointDescription(rgb_layout(rgb_w), packetized=True))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

        self.submodules.datapathr = PIXF2PIXDatapath(rgb16f_w, rgb_w)
        self.submodules.datapathg = PIXF2PIXDatapath(rgb16f_w, rgb_w)
        self.submodules.datapathb = PIXF2PIXDatapath(rgb16f_w, rgb_w)
        self.comb += self.datapathr.ce.eq(self.pipe_ce)
        self.comb += self.datapathg.ce.eq(self.pipe_ce)
        self.comb += self.datapathb.ce.eq(self.pipe_ce)

        self.comb += getattr(self.datapathr.sink, "pixf").eq(getattr(sink, "r_f"))
        self.comb += getattr(self.datapathg.sink, "pixf").eq(getattr(sink, "g_f"))
        self.comb += getattr(self.datapathb.sink, "pixf").eq(getattr(sink, "b_f"))

        self.comb += getattr(source, "r").eq(getattr(self.datapathr.source, "pix"))
        self.comb += getattr(source, "g").eq(getattr(self.datapathg.source, "pix"))
        self.comb += getattr(source, "b").eq(getattr(self.datapathb.source, "pix"))
