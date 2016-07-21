# rgb2rgb16f

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.flow.actor import *

from gateware.csc.common import *


def lookup_table(pix_val):
    '''
    Contents of lut list generated using int2float functions from 
    litex.csc.test.common 
    '''
    lut = [
        0     ,7168  ,8192  ,8704  ,9216  ,9472  ,9728  ,9984  ,
        10240 ,10368 ,10496 ,10624 ,10752 ,10880 ,11008 ,11136 ,
        11264 ,11328 ,11392 ,11456 ,11520 ,11584 ,11648 ,11712 ,
        11776 ,11840 ,11904 ,11968 ,12032 ,12096 ,12160 ,12224 ,
        12288 ,12320 ,12352 ,12384 ,12416 ,12448 ,12480 ,12512 ,
        12544 ,12576 ,12608 ,12640 ,12672 ,12704 ,12736 ,12768 ,
        12800 ,12832 ,12864 ,12896 ,12928 ,12960 ,12992 ,13024 ,
        13056 ,13088 ,13120 ,13152 ,13184 ,13216 ,13248 ,13280 ,
        13312 ,13328 ,13344 ,13360 ,13376 ,13392 ,13408 ,13424 ,
        13440 ,13456 ,13472 ,13488 ,13504 ,13520 ,13536 ,13552 ,
        13568 ,13584 ,13600 ,13616 ,13632 ,13648 ,13664 ,13680 ,
        13696 ,13712 ,13728 ,13744 ,13760 ,13776 ,13792 ,13808 ,
        13824 ,13840 ,13856 ,13872 ,13888 ,13904 ,13920 ,13936 ,
        13952 ,13968 ,13984 ,14000 ,14016 ,14032 ,14048 ,14064 ,
        14080 ,14096 ,14112 ,14128 ,14144 ,14160 ,14176 ,14192 ,
        14208 ,14224 ,14240 ,14256 ,14272 ,14288 ,14304 ,14320 ,
        14336 ,14344 ,14352 ,14360 ,14368 ,14376 ,14384 ,14392 ,
        14400 ,14408 ,14416 ,14424 ,14432 ,14440 ,14448 ,14456 ,
        14464 ,14472 ,14480 ,14488 ,14496 ,14504 ,14512 ,14520 ,
        14528 ,14536 ,14544 ,14552 ,14560 ,14568 ,14576 ,14584 ,
        14592 ,14600 ,14608 ,14616 ,14624 ,14632 ,14640 ,14648 ,
        14656 ,14664 ,14672 ,14680 ,14688 ,14696 ,14704 ,14712 ,
        14720 ,14728 ,14736 ,14744 ,14752 ,14760 ,14768 ,14776 ,
        14784 ,14792 ,14800 ,14808 ,14816 ,14824 ,14832 ,14840 ,
        14848 ,14856 ,14864 ,14872 ,14880 ,14888 ,14896 ,14904 ,
        14912 ,14920 ,14928 ,14936 ,14944 ,14952 ,14960 ,14968 ,
        14976 ,14984 ,14992 ,15000 ,15008 ,15016 ,15024 ,15032 ,
        15040 ,15048 ,15056 ,15064 ,15072 ,15080 ,15088 ,15096 ,
        15104 ,15112 ,15120 ,15128 ,15136 ,15144 ,15152 ,15160 ,
        15168 ,15176 ,15184 ,15192 ,15200 ,15208 ,15216 ,15224 ,
        15232 ,15240 ,15248 ,15256 ,15264 ,15272 ,15280 ,15288 ,
        15296 ,15304 ,15312 ,15320 ,15328 ,15336 ,15344 ,15352 
    ]
    return lut[pix_val]

class LeadOne(Module):
    def __init__(self):

        self.datai = Signal(8)
        self.leadone = Signal(4)
        for j in range(8):
            self.comb += If(self.datai[j], self.leadone.eq(8 - j-1))

@DecorateModule(InsertCE)
class PIX2PIXFLUT(Module):
    """ 
    Converts a 8 bit unsigned int represented by a pixel in 
    the range [0-255] to a 16 bit half precision floating point 
    pix_number defined in the range [0-1], using a look table
    """
    latency = 1

    def __init__(self, pix_w, pixf_w):
        self.sink = sink = Record(pix_layout(pix_w))
        self.source = source = Record(pixf_layout(pixf_w))

        # # #

        # delay pix signal
        pix_delayed = [sink]
        for i in range(self.latency):
            pix_n = Record(pix_layout(pix_w))
            self.sync += getattr(pix_n, "pix").eq(getattr(pix_delayed[-1], "pix"))
            pix_delayed.append(pix_n)

        # Hardware implementation:

        # Stage 1
        for j in range(256):
            self.sync += If(sink.pix==j, source.pixf.eq(lookup_table(j)))

@DecorateModule(InsertCE)
class PIX2PIXFDatapath(Module):
    """ Converts a 8 bit unsigned int represented by a pixel in 
    the range [0-255] to a 16 bit half precision floating point 
    pix_number defined in the range [0-1] """

    latency = 2
    def __init__(self, pix_w, pixf_w):
    
        self.sink = sink = Record(pix_layout(pix_w))
        self.source = source = Record(pixf_layout(pixf_w))

        # # #

        # delay pix signal
        pix_delayed = [sink]
        for i in range(self.latency):
            pix_n = Record(pix_layout(pix_w))
            self.sync += getattr(pix_n, "pix").eq(getattr(pix_delayed[-1], "pix"))
            pix_delayed.append(pix_n)

        # Hardware implementation:

        # Stage 1
        # Leading one detector

        lshift = Signal(4)
        frac_val = Signal(10)

        self.submodules.l1 = LeadOne()
        self.comb += [
            self.l1.datai.eq(sink.pix)
        ]

        self.sync += [

            lshift.eq(self.l1.leadone),
            frac_val[3:].eq(sink.pix[:7]),
            frac_val[:3].eq(0)
        ]

        # Stage 2
        # Adjust frac and exp components as per lshift
        # Pack in 16bit float

        self.sync += [
            source.pixf[:10].eq(frac_val << lshift),
            source.pixf[10:15].eq(15 - 1 - lshift),
            source.pixf[15].eq(1)
        ]
        
class RGB2RGB16f(PipelinedActor, Module):
    def __init__(self, rgb_w=8, rgb16f_w=16):
        self.sink = sink = Sink(EndpointDescription(rgb_layout(rgb_w), packetized=True))
        self.source = source = Source(EndpointDescription(rgb16f_layout(rgb16f_w), packetized=True))

        # # #

        for name in ["r", "g", "b"]:
            self.submodules.datapath = PIX2PIXFLUT(rgb_w, rgb16f_w)
            PipelinedActor.__init__(self, self.datapath.latency)
            self.comb += self.datapath.ce.eq(self.pipe_ce)
            self.comb += getattr(self.datapath.sink, "pix").eq(getattr(sink, name))
            self.comb += getattr(source, name + "f").eq(getattr(self.datapath.source, "pixf"))

        self.latency = self.datapath.latency
