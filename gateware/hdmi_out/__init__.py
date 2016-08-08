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
    def __init__(self, pads, lasmim, external_clocking=None):
        pack_factor = lasmim.dw//bpp

        if hasattr(pads, "scl"):
            self.submodules.i2c = I2C(pads)

        g = DataFlowGraph()

        # Define Modules
        self.pg = PixelGather(ndmas, pack_factor)
        mixer = MixerBlock(pixel_layout_c, pixel_layout)
        vtg = VTG(pack_factor)
        self.driver = Driver(pack_factor, pads, external_clocking)

        # Define Connections
        g_add_connection(self.pg, mixer)
        g.add_connection(self.pg.fi, vtg, source_subr=self.pg.fi.timing_subr, sink_ep="timing")
        g.add_connection(mixer, vtg, sink_ep="pixels")
        g.add_connection(vtg, self.driver)
        self.submodules += CompositeActor(g)

class PixelGather(Module, AutoCSR):
    def __init__(self, ndmas, pack_factor):

        combine_layout = [pixel_layout for i in range(ndmas)]

        self.fi = FrameInitiator(lasmim.aw, pack_factor, ndmas)
        combiner = Combinator(pixel_layout_c, combine_layout)

        for i in range(ndmas):

            # Define Modules
            intseq = misc.IntSequence(lasmim.aw, lasmim.aw)
            dma_out = AbstractActor(plumbing.Buffer)
            cast = structuring.Cast(lasmim.dw, pixel_layout(pack_factor), reverse_to=True)
            lasmim = self.sdram.crossbar.get_master()

            # Define Connections
            g.add_connection(self.fi, intseq, source_subr=self.fi.dma_subr(i))
            g.add_pipeline(intseq, AbstractActor(plumbing.Buffer), dma_lasmi.Reader(lasmim), dma_out, cast)
            g.add_connection(cast, combiner, sink_ep="sink"+str(n))

