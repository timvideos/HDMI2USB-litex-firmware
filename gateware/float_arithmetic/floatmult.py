'''
FloatMultDatapath class: Multiply two floating point numbers a and b, returns 
their output c in the same float16 format.

FloatMult class: Use the FloatMultDatapath above and generates a modules 
implemented using five stage pipeline.
'''

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *
from migen.flow.actor import *

from gateware.float_arithmetic.common import *

class LeadOne(Module):
    """
    This return the position of leading one of the Signal Object datai, as the 
    leadone Signal object. Function input dw defines the data width of datai 
    Signal object.
    """
    def __init__(self,dw):
        self.datai = Signal(dw)
        self.leadone = Signal(max=dw)
        for j in range(dw):
            self.comb += If(self.datai[j], self.leadone.eq(dw - j-1))

@DecorateModule(InsertCE)
class FloatMultDatapath(Module):
    """
    This adds a floating point multiplication unit.
    Inputs: in1 and in2
    Output: out
    Implemented as a 5 stage pipeline, design is based on float16 design doc. 
    Google Docs Link: https://goo.gl/Rvx2B7    
    """
    latency = 5
    def __init__(self, dw):
        self.sink = sink = Record(in_layout(dw))
        self.source = source = Record(out_layout(dw))

        # delay rgb signals
        in_delayed = [sink]
        for i in range(self.latency):
            in_n = Record(in_layout(dw))
            for name in ["in1", "in2"]:
                self.sync += getattr(in_n, name).eq(getattr(in_delayed[-1], name))
            in_delayed.append(in_n)

        # stage 1
        # Unpack
        # Look for special cases

        in1_mant = Signal(11)
        in2_mant = Signal(11)

        in1_exp1 = Signal(5)
        in2_exp1 = Signal(5)

#        in1_sign = Signal()
#        in2_sign = Signal()

        out_status1 = Signal(2)
        status_stage1 = Signal(16)
        # 00-0 Zero
        # 01-1 Inf
        # 10-2 Nan
        # 11-3 Normal 
        
        self.sync += [
            If(sink.in1[10:15]==0,
                in1_mant.eq( Cat(sink.in1[:10], 0)),     
                in1_exp1.eq(sink.in1[10:15] + 1 )       
            ).Else(
                in1_mant.eq( Cat(sink.in1[:10], 1)),
                in1_exp1.eq(sink.in1[10:15])
            ),

            If(sink.in2[10:15]==0,
                in2_mant.eq( Cat(sink.in2[:10], 0)),     
                in2_exp1.eq(sink.in2[10:15] + 1 )       
            ).Else(
                in2_mant.eq( Cat(sink.in2[:10], 1)),
                in2_exp1.eq(sink.in2[10:15])
            ),  
            out_status1.eq(3),
            status_stage1.eq(sink.in2[10:15])
        ]

        # stage 2
        # Multiply fractions and add exponents
        out_mult = Signal(22)
        out_exp = Signal((7,True))
        out_status2 = Signal(2)        
        status_stage2 = Signal(16)

        self.sync += [
            out_mult.eq(in1_mant * in2_mant),
            out_exp.eq(in1_exp1 + in2_exp1 - 15),
            out_status2.eq(out_status1),
            status_stage2.eq(status_stage1)
        ]

        # stage 3
        # Leading one detector
        one_ptr = Signal(5)
        out_status3 = Signal(2)
        out_mult3 = Signal(22)
        out_exp3 = Signal((7,True))
        status_stage3 = Signal(16)

        lead_one_ptr = Signal(5)
        self.submodules.leadone = LeadOne(22)
        self.comb += [
            self.leadone.datai.eq(out_mult),
            lead_one_ptr.eq(self.leadone.leadone)
        ]

        self.sync += [
            out_status3.eq(out_status2),
            out_mult3.eq(out_mult),
            out_exp3.eq(out_exp),
            one_ptr.eq(lead_one_ptr),
            status_stage3.eq(status_stage2)
        ]

        # stage 4
        # Shift and Adjust
        out_exp_adjust = Signal((7,True))
        out_mult_shift = Signal(22)
        out_status4 = Signal(2)
        status_stage4 = Signal(16)

        self.sync += [
            out_status4.eq(3),
            If((out_exp3 - one_ptr) < 1,
                out_exp_adjust.eq(0),
                out_mult_shift.eq(((out_mult3 >> (0-out_exp3)) << 1))
            ).Else(
                out_exp_adjust.eq(out_exp3 +1 - one_ptr),
                out_mult_shift.eq(out_mult3 << one_ptr+1)
            ),

        ]

        # stage 5
        # Normalize and pack
        self.sync += [
            If(out_status4 == 3,
                source.out.eq( Cat(out_mult_shift[12:], out_exp_adjust[:5],0) )
            ),
#            source.out.eq(status_stage4)
        ]



class FloatMult(PipelinedActor, Module, AutoCSR):
    def __init__(self, dw=16):
        self.sink = sink = Sink(EndpointDescription(in_layout(dw), packetized=True))
        self.source = source = Source(EndpointDescription(out_layout(dw), packetized=True))

        # # #

        self.submodules.datapath = FloatMultDatapath(dw)
        PipelinedActor.__init__(self, self.datapath.latency)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        for name in ["in1", "in2"]:
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))
        self.comb += getattr(source, "out").eq(getattr(self.datapath.source, "out"))
        self.latency = self.datapath.latency

#        self._float_in1 = CSRStorage(dw)
#        self._float_in2 = CSRStorage(dw)
#        self._float_out = CSRStatus(dw)

#        self.comb += [
#            getattr(sink, "in1").eq(self._float_in1.storage),
#            getattr(sink, "in2").eq(self._float_in2.storage),
#            self._float_out.status.eq(getattr(source, "out"))
#        ]


class FloatMultRGB(PipelinedActor, Module):
    def __init__(self, dw=16):
        self.sink = sink = Sink(EndpointDescription(rgb16f_layout(dw), packetized=True))
        self.source = source = Source(EndpointDescription(rgb16f_layout(dw), packetized=True))

        # # #

        for name in ["r", "g", "b"]:
            self.submodules.datapath = FloatMultDatapath(dw)
            PipelinedActor.__init__(self, self.datapath.latency)
            self.comb += self.datapath.ce.eq(self.pipe_ce)
            self.comb += getattr(self.datapath.sink, "in1").eq(getattr(sink, name + "f"))
            self.comb += getattr(self.datapath.sink, "in2").eq(14336) # 0.5
            self.comb += getattr(source, name + "f").eq(getattr(self.datapath.source, "out"))

        self.latency = self.datapath.latency
