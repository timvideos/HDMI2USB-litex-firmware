# rgb2ycbcr

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.flow.actor import *

from gateware.csc.common import *

datapath_latency = 2


@DecorateModule(InsertCE)
class RGB2RGB16fDatapath(Module):
    def __init__(self, rgb_w, rgb16f_w):
        self.sink = sink = Record(rgb_layout(rgb_w))
        self.source = source = Record(rgb16f_layout(rgb16f_w))

        # # #
        # delay rgb signals
        rgb_delayed = [sink]
        for i in range(datapath_latency):
            rgb_n = Record(rgb_layout(rgb_w))
            for name in ["r", "g", "b"]:
                self.sync += getattr(rgb_n, name).eq(getattr(rgb_delayed[-1], name))
            rgb_delayed.append(rgb_n)

        # Hardware implementation:

        # stage 1
        # Leading one detector

        r_lshift_val = Signal(3)
        g_lshift_val = Signal(3)
        b_lshift_val = Signal(3)

        r_frac_val = Signal(10)
        g_frac_val = Signal(10)
        b_frac_val = Signal(10)

        r_exp = Signal(5)
        g_exp = Signal(5)
        b_exp = Signal(5)

        # Leading one detector

        self.sync += [

            If( sink.r[7]==1,
                r_lshift_val.eq(0)
            ).Elif(sink.r[6] == 1,
                r_lshift_val.eq(1)
            ).Elif(sink.r[5] == 1,
                r_lshift_val.eq(2)
            ).Elif(sink.r[4] == 1,
                r_lshift_val.eq(3)
            ).Elif(sink.r[3] == 1,
                r_lshift_val.eq(4)
            ).Elif(sink.r[2] == 1,
                r_lshift_val.eq(5)
            ).Elif(sink.r[1] == 1,
                r_lshift_val.eq(6)
            ).Elif(sink.r[0] == 1,
                r_lshift_val.eq(7)
            ).Else(r_exp.eq(14)),

            If( sink.g[7]==1,
                g_lshift_val.eq(0)
            ).Elif(sink.g[6] == 1,
                g_lshift_val.eq(1)
            ).Elif(sink.g[5] == 1,
                g_lshift_val.eq(2)
            ).Elif(sink.g[4] == 1,
                g_lshift_val.eq(3)
            ).Elif(sink.g[3] == 1,
                g_lshift_val.eq(4)
            ).Elif(sink.g[2] == 1,
                g_lshift_val.eq(5)
            ).Elif(sink.g[1] == 1,
                g_lshift_val.eq(6)
            ).Elif(sink.g[0] == 1,
                g_lshift_val.eq(7)
            ).Else(g_exp.eq(14)),

            If( sink.b[7]==1,
                b_lshift_val.eq(0)
            ).Elif(sink.b[6] == 1,
                b_lshift_val.eq(1)
            ).Elif(sink.b[5] == 1,
                b_lshift_val.eq(2)
            ).Elif(sink.b[4] == 1,
                b_lshift_val.eq(3)
            ).Elif(sink.b[3] == 1,
                b_lshift_val.eq(4)
            ).Elif(sink.b[2] == 1,
                b_lshift_val.eq(5)
            ).Elif(sink.b[1] == 1,
                b_lshift_val.eq(6)
            ).Elif(sink.b[0] == 1,
                b_lshift_val.eq(7)
            ).Else(b_exp.eq(14)),

            r_frac_val[3:].eq(sink.r[:7]),
            g_frac_val[3:].eq(sink.g[:7]),
            b_frac_val[3:].eq(sink.b[:7]),

            r_frac_val[:3].eq(0),
            g_frac_val[:3].eq(0),
            b_frac_val[:3].eq(0),
        ]

        # stage 2

        r_frac_shifted = Signal(10)
        r_exp_val = Signal(5)

        self.sync += [

            source.r_f[:10].eq(r_frac_val << r_lshift_val),
            source.r_f[10:15].eq(15 - 1 - r_lshift_val),
            source.r_f[15].eq(0),

            source.g_f[:10].eq(g_frac_val << g_lshift_val),
            source.g_f[10:15].eq(15 - 1 - g_lshift_val),
            source.g_f[15].eq(0),

            source.b_f[:10].eq(b_frac_val << b_lshift_val),
            source.b_f[10:15].eq(15 - 1 - b_lshift_val),
            source.b_f[15].eq(0)

        ]
        
class RGB2RGB16f(PipelinedActor, Module):
    def __init__(self, rgb_w=8, rgb16f_w=16):
        self.sink = sink = Sink(EndpointDescription(rgb_layout(rgb_w), packetized=True))
        self.source = source = Source(EndpointDescription(rgb16f_layout(rgb16f_w), packetized=True))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

        self.submodules.datapath = RGB2RGB16fDatapath(rgb_w, rgb16f_w)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        for name in ["r", "g", "b"]:
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))
        for name in ["r_f", "g_f", "b_f"]:
            self.comb += getattr(source, name).eq(getattr(self.datapath.source, name))
