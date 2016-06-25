# rgb2ycbcr

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.flow.actor import *

from gateware.csc.common import *

datapath_latency = 2

@DecorateModule(InsertCE)
class PIX2PIXFDatapath(Module):
    def __init__(self, pix_w, pixf_w):
        self.sink = sink = Record(pix_layout(pix_w))
        self.source = source = Record(pixf_layout(pixf_w))

        # # #

        # delay pix signal
        pix_delayed = [sink]
        for i in range(datapath_latency):
            pix_n = Record(pix_layout(pix_w))
            self.sync += getattr(pix_n, "pix").eq(getattr(pix_delayed[-1], "pix"))
            pix_delayed.append(pix_n)

        # Hardware implementation:

        # stage 1
        # Leading one detector

        r_lshift_val = Signal(3)
        r_frac_val = Signal(10)
        r_exp = Signal(5)


        self.sync += [

            # Leading one detector
            If( sink.pix[7]==1,
                r_lshift_val.eq(0)
            ).Elif(sink.pix[6] == 1,
                r_lshift_val.eq(1)
            ).Elif(sink.pix[5] == 1,
                r_lshift_val.eq(2)
            ).Elif(sink.pix[4] == 1,
                r_lshift_val.eq(3)
            ).Elif(sink.pix[3] == 1,
                r_lshift_val.eq(4)
            ).Elif(sink.pix[2] == 1,
                r_lshift_val.eq(5)
            ).Elif(sink.pix[1] == 1,
                r_lshift_val.eq(6)
            ).Elif(sink.pix[0] == 1,
                r_lshift_val.eq(7)
            ).Else(r_exp.eq(14)),

            r_frac_val[3:].eq(sink.pix[:7]),
            r_frac_val[:3].eq(0)
        ]

        # stage 2

        self.sync += [

            source.pixf[:10].eq(r_frac_val << r_lshift_val),
            source.pixf[10:15].eq(15 - 1 - r_lshift_val),
            source.pixf[15].eq(1)

        ]
        
class RGB2RGB16f(PipelinedActor, Module):
    def __init__(self, rgb_w=8, rgb16f_w=16):
        self.sink = sink = Sink(EndpointDescription(rgb_layout(rgb_w), packetized=True))
        self.source = source = Source(EndpointDescription(rgb16f_layout(rgb16f_w), packetized=True))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

        self.submodules.datapathr = PIX2PIXFDatapath(rgb_w, rgb16f_w)
        self.submodules.datapathg = PIX2PIXFDatapath(rgb_w, rgb16f_w)
        self.submodules.datapathb = PIX2PIXFDatapath(rgb_w, rgb16f_w)
        self.comb += self.datapathr.ce.eq(self.pipe_ce)
        self.comb += self.datapathg.ce.eq(self.pipe_ce)
        self.comb += self.datapathb.ce.eq(self.pipe_ce)

        self.comb += getattr(self.datapathr.sink, "pix").eq(getattr(sink, "r"))
        self.comb += getattr(self.datapathg.sink, "pix").eq(getattr(sink, "g"))
        self.comb += getattr(self.datapathb.sink, "pix").eq(getattr(sink, "b"))
        self.comb += getattr(source, "r_f").eq(getattr(self.datapathr.source, "pixf"))
        self.comb += getattr(source, "g_f").eq(getattr(self.datapathg.source, "pixf"))
        self.comb += getattr(source, "b_f").eq(getattr(self.datapathb.source, "pixf"))
