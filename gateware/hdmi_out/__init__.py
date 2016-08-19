from migen.fhdl.std import *
from migen.flow.network import *
from migen.flow import plumbing
from migen.bank.description import AutoCSR
from migen.actorlib import structuring, misc

from misoclib.mem.sdram.frontend import dma_lasmi
from gateware.hdmi_out.format import bpp, pixel_layout, pixel_layout_c, FrameInitiator, VTG
from gateware.hdmi_out.phy import Driver
from gateware.i2c import I2C


class HDMIOut(Module, AutoCSR):
    """HDMIOut Module
    
    The HDMIOut Module defined the neccesary objects and function neccesary to 
    read HDMI_OUT data from relevant base address from main memory and output 
    that data to corresponding HDMI_OUT port. 

    This is derived from standard VGA core, description can be found here. 
    https://migen.readthedocs.io/en/latest/casestudies.html

    The blockdiagram corresponding to reworked HDMI_OUT are added here.
    <add a permanent doc link with all block diagrams added>

    Parameters
    ----------
    pads: ???
        This contains the information regarding the FPGA pins that are mapped to
        HDMi_OUT pins. 

    dma: ???
        Instance of sdram class defined in target file for DMA access.  
    
    ndmas: int
        Number of DMA engines to be initiated, specified in target file. 

    external_clocking: ???
        Clocking realted information, by default None defined in Driver class
    
    """
    def __init__(self, pads, dma, ndmas=1, external_clocking=None):

        if hasattr(pads, "scl"):
            self.submodules.i2c = I2C(pads)

        lasmim_list = [dma.crossbar.get_master() for i in range(ndmas)]
        pack_factor = lasmim_list[0].dw//bpp
        g = DataFlowGraph()

        # Define Modules

        self.fi = FrameInitiator(lasmim_list[0].aw, pack_factor, ndmas)
        self.pg = PixelGather(self.fi, lasmim_list, pack_factor, ndmas, g)
        vtg = VTG(pack_factor, ndmas)
        self.driver = Driver(pack_factor, ndmas, pads, external_clocking)

        # Define Connections

        g.add_connection(self.pg.combiner, vtg , sink_ep='pixels')
        g.add_connection(self.pg.fi, vtg, source_subr=self.pg.fi.timing_subr, sink_ep="timing")
        g.add_connection(vtg, self.driver)

        self.submodules += CompositeActor(g)

class PixelGather(Module):
    """Pixel Gathere Module
    
    The Pixel Gather module defines number of dma engines. Each dma gets
    it base address from FrameInitiator Module. Each DMA outputs a data of
    the form pixel_layout() and these are combined in a single layout
    pixel_layout_c() using DMACombinator, which is the final output of this
    module. 
    
    This is derived from standard VGA core, description can be found here. 
    https://migen.readthedocs.io/en/latest/casestudies.html

    Parameters
    ----------
    fi: FrameInitiator
        Instance of FrameInitiator() class defined in HDMIOut. 
    
    lasmim_list: list
        List of dma.crossbar.get_master() to define each DMA. 
    
    pack_factor: int
        DMA Data Width/data per pixel or number of pixels read in a time from DMA. 

    ndmas: int
        Number of DMA engines to be initiated, specified in target file. 
    
    g: DataFlowGraph
        Instance of DataFlowGraph() class, defined in HDMIOut. 

    Attributes
    ----------
    fi : list of Signals, in
        Instance of FrameInitiator class. 
    combiner : Instance of DMACombinat class, out
        Output from each DMA combined in a single layout.  
    """
    def __init__(self, fi, lasmim_list, pack_factor, ndmas, g):

        combine_layout = [pixel_layout(pack_factor) for i in range(ndmas)]

        self.fi = fi
        self.combiner = DMACombinator(pixel_layout_c(pack_factor, ndmas), combine_layout, ndmas)

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


class DMACombinator(Module):
    """DMACombinator Module
    
    This is a simple combinatonal block which takes pixel_layout() signals from 
    each of the dma and combines them to a single layout pixel_layout_c().

    Parameters
    ----------
    layout: list
        This represents the complete layout at output that is pixel_layout_c()

    subrecords: list
        List of containg pixel_layout() repeated ndmas times
    
    ndmas: int
        Number of DMA engines to be initiated, specified in target file    
    
    Attributes
    ----------
    source : Source class, out
        EndPointDescription of output layout

    sink0 : Sink class, in
        EndPointDescription of input layout
        Similarly for all other instantiations of Sink

    """    
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

