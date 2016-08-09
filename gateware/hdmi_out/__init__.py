from migen.fhdl.std import *
from migen.flow.network import *
from migen.flow import plumbing
from migen.bank.description import AutoCSR
from migen.actorlib import structuring, misc

from misoclib.mem.sdram.frontend import dma_lasmi
from gateware.hdmi_out.format import bpp, pixel_layout, pixel_layout_c, FrameInitiator, VTG
from gateware.hdmi_out.phy import Driver
from gateware.hdmi_out.mixing import MixerBlock
from gateware.i2c import I2C


class HDMIOut(Module, AutoCSR):
    def __init__(self, pads, lasmim, ndmas, external_clocking=None):
        pack_factor = lasmim.dw//bpp

        if hasattr(pads, "scl"):
            self.submodules.i2c = I2C(pads)

        g = DataFlowGraph()
        lasmim_list = [lasmim]

        # Define Modules
        self.fi = FrameInitiator(lasmim_list[0].aw, pack_factor, ndmas)        
        self.pg = PixelGather(self.fi, lasmim_list, ndmas, pack_factor, g)
        mixer = MixerBlock(pixel_layout_c(pack_factor, ndmas), pixel_layout(pack_factor), pack_factor)
        vtg = VTG(pack_factor)
        self.driver = Driver(pack_factor, pads, external_clocking)

        # Define Connections
        g.add_connection(self.pg.combiner, mixer)

        g.add_connection(self.pg.fi, vtg, source_subr=self.pg.fi.timing_subr, sink_ep="timing")
        g.add_connection(mixer, vtg, sink_ep="pixels")
        g.add_connection(vtg, self.driver)

        self.submodules += CompositeActor(g)

class PixelGather(Module):
    def __init__(self, fi, lasmim_list, ndmas, pack_factor, g):

        combine_layout = [pixel_layout(pack_factor) for i in range(ndmas)]

        self.fi = fi
        self.combiner = Combinat(pixel_layout_c(pack_factor, ndmas), combine_layout, ndmas)

        for i in range(ndmas):

            # Define Modules
            lasmimb = lasmim_list[i]
            intseq = misc.IntSequence(lasmimb.aw, lasmimb.aw)
            dma_out = AbstractActor(plumbing.Buffer)
            cast = structuring.Cast(lasmimb.dw, pixel_layout(pack_factor), reverse_to=True)

            # Define Connections
            g.add_connection(self.fi, intseq, source_subr=self.fi.dma_subr(i))
            g.add_pipeline(intseq, AbstractActor(plumbing.Buffer), dma_lasmi.Reader(lasmimb), dma_out, cast)
            g.add_connection(cast, self.combiner, sink_ep="sink"+str(i))


class Combinat(Module):
    def __init__(self, layout, subrecords, ndmas):
        self.source = Source(layout)    # pixel_layout_c
        sinks = []
        for n, r in enumerate(subrecords):
            s = Sink(r)
            setattr(self, "sink"+str(n), s)
            sinks.append(s)             # pixel_layout
        self.busy = Signal()

        ###

        self.comb += [
            self.busy.eq(0),
            self.source.stb.eq(optree("&", [sink.stb for sink in sinks]))
        ]

        self.comb += [sink.ack.eq(self.source.ack & self.source.stb) for sink in sinks]
        self.comb += [self.source.param.eq(sink.param) for sink in sinks]

        for i in range(ndmas):
            self.comb += [ getattr(self.source.payload, "n"+str(i) ).eq(sinks[i].payload)]
#            getattr(self.source.payload, "n"+str(i) )
#            sinks[i].payload

