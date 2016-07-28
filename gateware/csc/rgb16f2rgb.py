# rgb16f2rgb

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.flow.actor import *

from gateware.csc.common import *

@DecorateModule(InsertCE)
class PIXF2PIXDatapath(Module):
    """ 
    Converts a 16 bit half precision floating point 
    number defined in the range [0-1] to 8 bit unsigned 
    int represented by a pixel in the range [0-255]
    """
    latency = 2
    def __init__(self, pixf_w, pix_w):
        self.sink = sink = Record(pixf_layout(pixf_w))
        self.source = source = Record(pix_layout(pix_w))

        # # #

        # delay pixf signals
        pixf_delayed = [sink]
        for i in range(self.latency):
            pixf_n = Record(pixf_layout(pixf_w))
            self.sync += getattr(pixf_n, "pixf").eq(getattr(pixf_delayed[-1], "pixf"))
            pixf_delayed.append(pixf_n)


        # Hardware implementation:

        # Stage 1
        # Unpack frac and exp components
        # Correct exponent offset for shifting later
        frac = Signal(11)
        exp = Signal(5)
        exp_offset = Signal(5)
		
        self.sync += [
        
            exp_offset.eq(15 - sink.pixf[10:15] -1),    
            frac[:10].eq(sink.pixf[:10]),
            frac[10].eq(1),
        ]

        # Stage 2
        # Right shift frac by exp_offset
        # Most significant 8 bits of frac assigned to uint8 pix 
        self.sync += [
            source.pix.eq( (frac >> exp_offset)[3:]),
        ]


class RGB16f2RGB(PipelinedActor, Module):
    def __init__(self, rgb16f_w=16, rgb_w=8, coef_w=8):
        self.sink = sink = Sink(EndpointDescription(rgb16f_layout(rgb16f_w), packetized=True))
        self.source = source = Source(EndpointDescription(rgb_layout(rgb_w), packetized=True))

        # # #

        for name in ["r", "g", "b"]:
            self.submodules.datapath = PIXF2PIXDatapath(rgb16f_w, rgb_w)
            PipelinedActor.__init__(self, self.datapath.latency)
            self.comb += self.datapath.ce.eq(self.pipe_ce)
            self.comb += getattr(self.datapath.sink, "pixf").eq(getattr(sink, name +"f"))
            self.comb += getattr(source, name).eq(getattr(self.datapath.source, "pix"))

        self.latency = self.datapath.latency
