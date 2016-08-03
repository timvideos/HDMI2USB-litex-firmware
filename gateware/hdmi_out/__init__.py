from migen.fhdl.std import *
from migen.flow.network import *
from migen.flow import plumbing
from migen.bank.description import AutoCSR
from migen.actorlib import structuring, misc

from misoclib.mem.sdram.frontend import dma_lasmi
from gateware.hdmi_out.format import bpp, pixel_layout, FrameInitiator, VTG
from gateware.hdmi_out.phy import Driver
from gateware.i2c import I2C


class HDMIOut(Module, AutoCSR):
    def __init__(self, pads, lasmim, external_clocking=None):
        pack_factor = lasmim.dw//bpp

        if hasattr(pads, "scl"):
            self.submodules.i2c = I2C(pads)

        g = DataFlowGraph()

#        self.fi = FrameInitiator(lasmim.aw, pack_factor)
        self.fi = FrameInitiator(lasmim.aw, pack_factor, ndmas=2)

        intseq0 = misc.IntSequence(lasmim.aw, lasmim.aw)
        intseq1 = misc.IntSequence(lasmim.aw, lasmim.aw)

        dma_out0 = AbstractActor(plumbing.Buffer)
        dma_out1 = AbstractActor(plumbing.Buffer)

        g.add_connection(self.fi, intseq0, source_subr=self.fi.dma_subr(0))
        g.add_connection(self.fi, intseq1, source_subr=self.fi.dma_subr(1))

        g.add_pipeline(intseq0, AbstractActor(plumbing.Buffer), dma_lasmi.Reader(lasmim), dma_out0)
        g.add_pipeline(intseq1, AbstractActor(plumbing.Buffer), dma_lasmi.Reader(lasmim), dma_out1)

        cast0 = structuring.Cast(lasmim.dw, pixel_layout(pack_factor), reverse_to=True)
        cast1 = structuring.Cast(lasmim.dw, pixel_layout(pack_factor), reverse_to=True)

        vtg = VTG(pack_factor)
        self.driver = Driver(pack_factor, pads, external_clocking)

        g.add_connection(self.fi, vtg, source_subr=self.fi.timing_subr, sink_ep="timing")
        g.add_connection(dma_out0, cast0)
        g.add_connection(dma_out1, cast1)
        g.add_connection(cast0, vtg, sink_ep="pixels0")
        g.add_connection(cast1, vtg, sink_ep="pixels1")
        g.add_connection(vtg, self.driver)
        self.submodules += CompositeActor(g)
