from migen.fhdl.std import *
from migen.flow.network import *


class MixerBlock(Module):
    def __init__(self, layout_in, layout_out):
        self.sink = Sink(layout_in)
        self.source = Source(layout_out)
        self.busy = Signal()
        i = 0

        ###

        self.comb += [
            self.busy.eq(0),
            self.source.stb.eq(self.sink.stb),
            self.sink.ack.eq(self.source.ack & self.source.stb)
        ]

        self.comb += [self.source.payload.eq(getattr(self.sink.payload, "n"+str(i)))]
