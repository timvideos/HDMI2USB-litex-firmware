from migen.fhdl.std import *
from migen.flow.network import *


class MixerBlock(Module):
    def __init__(self, layout_in, layout_out):
        self.sink = Sink(layout_in)
        self.source = Source(layout_out)
        self.busy = Signal()

        ###

        self.comb += [
            self.busy.eq(0),
            self.source.stb.eq(self.sink.stb),
            self.sink.ack.eq(self.source.ack & self.source.stb)
        ]

        i = 4
		self.comb += [self.source.payload.n0.eq(getattr(self.sink, "n"+i))]
