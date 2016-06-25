# rgb16f2rgb

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.flow.actor import *

from gateware.csc.common import *

datapath_latency = 2

@DecorateModule(InsertCE)
class RGB16f2RGBDatapath(Module):
    def __init__(self, rgb16f_w, rgb_w):
        self.sink = sink = Record(rgb16f_layout(rgb16f_w))
        self.source = source = Record(rgb_layout(rgb_w))

        # # #

        # delay rgb16f signals
        rgb16f_delayed = [sink]
        for i in range(datapath_latency):
            rgb16f_n = Record(rgb16f_layout(rgb16f_w))
            for name in ["r_f", "g_f", "b_f"]:
                self.sync += getattr(rgb16f_n, name).eq(getattr(rgb16f_delayed[-1], name))
            rgb16f_delayed.append(rgb16f_n)


        # Hardware implementation:
        # Float is defines in the range [0-1] (higher precision)
        # Uint8 is defined in the range [0-255]

        # stage 1
        # Unpack
        # Correct exponent offset for shifting later

        r_frac = Signal(11)
        g_frac = Signal(11)
        b_frac = Signal(11)

        r_exp = Signal(5)
        g_exp = Signal(5)
        b_exp = Signal(5)

        r_exp_offset = Signal(5)
        g_exp_offset = Signal(5)
        b_exp_offset = Signal(5)
		
        self.sync += [
        
            r_exp_offset.eq(15 - sink.r_f[10:15] -1),    
            g_exp_offset.eq(15 - sink.g_f[10:15] -1),    
            b_exp_offset.eq(15 - sink.b_f[10:15] -1),

            r_frac[:10].eq(sink.r_f[:10]),
            g_frac[:10].eq(sink.g_f[:10]),
            b_frac[:10].eq(sink.b_f[:10]),

            r_frac[10].eq(1),
            g_frac[10].eq(1),
            b_frac[10].eq(1)
        ]

        # stage 2
        # Right shift r_frac by r_exp_offset
        # r_exp_offset = 1
        # Most significant 8 bits of r_frac assigned to int8 r

        self.sync += [
            source.r.eq( (r_frac >> r_exp_offset)[3:]),
            source.g.eq( (g_frac >> g_exp_offset)[3:]),
            source.b.eq( (b_frac >> b_exp_offset)[3:])

        ]


class RGB16f2RGB(PipelinedActor, Module):
    def __init__(self, rgb16f_w=16, rgb_w=8, coef_w=8):
        self.sink = sink = Sink(EndpointDescription(rgb16f_layout(rgb16f_w), packetized=True))
        self.source = source = Source(EndpointDescription(rgb_layout(rgb_w), packetized=True))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

        self.submodules.datapath = RGB16f2RGBDatapath(rgb16f_w, rgb_w)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        for name in ["r_f", "g_f", "b_f"]:
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))
        for name in ["r", "g", "b"]:
            self.comb += getattr(source, name).eq(getattr(self.datapath.source, name))
