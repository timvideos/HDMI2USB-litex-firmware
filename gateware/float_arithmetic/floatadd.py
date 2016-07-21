'''
FloatAddDatapath class: Add two floating point numbers in1 and in2, returns 
their output out in the same float16 format.

FloatAdd class: Use the FloatAddDatapath above and generates a pipelined
module implemented using five stage pipeline.
'''

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *
from migen.flow.actor import *

from gateware.float_arithmetic.common import *

datapath_latency = 5

class LeadOne(Module):
    def __init__(self):

        self.datai = Signal(12)
        self.leadone = Signal(4)
        for j in range(12):
            self.comb += If(self.datai[j], self.leadone.eq(12 - j-1))

@DecorateModule(InsertCE)
class FloatAddDatapath(Module):
    
    latency = 5
    
    def __init__(self,dw):
        self.sink = sink = Record(in_layout(dw))
        self.source = source = Record(out_layout(dw))

        # delay rgb signals
        in_delayed = [sink]
        for i in range(self.latency):
            in_n = Record(in_layout(dw))
            for name in ["in1", "in2"]:
                self.sync += getattr(in_n, name).eq(getattr(in_delayed[-1], name))
            in_delayed.append(in_n)

        # Hardware implementation:

        # Stage 1
        # Unpack
        # Substract Exponents

        in1_frac = Signal(10)
        in2_frac = Signal(10)
        
        in1_mant = Signal(11)
        in2_mant = Signal(11)

        in1_exp = Signal(5)
        in2_exp = Signal(5)

        in1_minus_in2_exp = Signal((6,True))

        in1_exp1 = Signal(5)
        in2_exp1 = Signal(5)

        in1_sign = Signal()
        in2_sign = Signal()


        out_status1 = Signal(2)
        # 00-0 Zero
        # 01-1 Inf
        # 10-2 Nan
        # 11-3 Normal 
        
        in1_stage1 = Signal(16)
        in2_stage1 = Signal(16)

        self.comb += [
            in1_frac.eq( sink.in1[:10] ),
            in2_frac.eq( sink.in2[:10] ),

            in1_exp.eq( sink.in1[10:15] ),
            in2_exp.eq( sink.in2[10:15] ),

            in1_sign.eq( sink.in1[15] ),
            in2_sign.eq( sink.in1[15] ),

        ]

        self.comb += [
            If( in1_exp==0,
                in1_mant.eq( Cat(sink.in1[:10], 0)),     
                in1_exp1.eq( sink.in1[10:15] + 1 )       
            ).Else(
                in1_mant.eq( Cat(sink.in1[:10], 1)),
                in1_exp1.eq( sink.in1[10:15])
            ),

            If( in2_exp==0,
                in2_mant.eq( Cat(sink.in2[:10], 0)),     
                in2_exp1.eq( sink.in2[10:15] + 1 )       
            ).Else(
                in2_mant.eq( Cat(sink.in2[:10], 1)),
                in2_exp1.eq( sink.in2[10:15])
            )
        ]

        in1_frac_stage1 = Signal(11)
        in2_frac_stage1 = Signal(11)
        in1_sign_stage1 = Signal(11)
        in2_sign_stage1 = Signal(11)
        in1_exp_stage1 = Signal(5)
        in2_exp_stage1 = Signal(5)

        self.sync += [

            in1_minus_in2_exp.eq(in1_exp1 - in2_exp),
            in1_frac_stage1.eq(in1_mant),   
            in2_frac_stage1.eq(in2_mant),   
            in1_exp_stage1.eq(in1_exp1),   
            in2_exp_stage1.eq(in2_exp1),   
            in1_sign_stage1.eq(in1_sign),
            in2_sign_stage1.eq(in2_sign),
            out_status1.eq(3),

        ]

        # Stage 2
        # Adjust both the input fracs to common exponent
        in1_frac_stage2 = Signal(11)
        in2_frac_stage2 = Signal(11)
        in1_sign_stage2 = Signal(11)
        in2_sign_stage2 = Signal(11)
        in1_minus_in2_exp_stage2 = Signal(5)
        out_2 = Signal(16)

        self.sync += [

            If( ~in1_minus_in2_exp[5], [
                in2_frac_stage2.eq(in2_frac_stage1 >> in1_minus_in2_exp),
                in1_frac_stage2.eq(in1_frac_stage1),
                in1_minus_in2_exp_stage2.eq(in1_exp_stage1)
                ]
            ).Else ( [
                in1_frac_stage2.eq(in1_frac_stage1 >> (-1)*in1_minus_in2_exp ),
                in1_minus_in2_exp_stage2.eq(in2_exp_stage1),
                in2_frac_stage2.eq(in2_frac_stage1),
                ]
            ),
            in1_sign_stage2.eq(in1_sign_stage1),
            in2_sign_stage2.eq(in2_sign_stage1),
        ]

        # Stage 3
        # Adder Unit
        in1_plus_in2_frac = Signal(12)
        in1_plus_in2_sign = Signal(1)
        in1_minus_in2_exp_stage3 = Signal(5)
        out_3 = Signal(16)

        self.sync += [
            Cat(in1_plus_in2_frac, in1_plus_in2_sign).eq(in1_frac_stage2+in2_frac_stage2),
            in1_minus_in2_exp_stage3.eq(in1_minus_in2_exp_stage2),
            out_3.eq(out_2)
        ]

        # Stage 4
        # Shift and Adjust
        leadone = Signal(4)
        self.submodules.l1 = LeadOne()
        self.comb += [
            self.l1.datai.eq(in1_plus_in2_frac),
            leadone.eq(self.l1.leadone)
        ]
        out_sign_stage4 = Signal(1)   
        out_frac_stage4 = Signal(12)  
        out_exp_stage4 = Signal(5)
        out_4 = Signal(16)
        self.sync += [
            out_frac_stage4.eq(in1_plus_in2_frac << (leadone)),
            out_exp_stage4.eq(in1_minus_in2_exp_stage3 - leadone + 1 ),
            out_sign_stage4.eq(in1_plus_in2_sign),
            out_4.eq(out_frac_stage4)
        ]

        # stage 5
        # Normalize and pack
        self.sync += [
            source.out.eq( Cat( out_frac_stage4[1:11] , out_exp_stage4 ,out_sign_stage4 ) )
        ]


class FloatAddRGB(PipelinedActor, Module):
    def __init__(self, dw=16):
        self.sink = sink = Sink(EndpointDescription(rgb16f_layout(dw), packetized=True))
        self.source = source = Source(EndpointDescription(rgb16f_layout(dw), packetized=True))

        # # #

        for name in ["r", "g", "b"]:
            self.submodules.datapath = FloatAddDatapath(dw)
            PipelinedActor.__init__(self, self.datapath.latency)
            self.comb += self.datapath.ce.eq(self.pipe_ce)
            self.comb += getattr(self.datapath.sink, "in1").eq(getattr(sink, name + "f"))
            self.comb += getattr(self.datapath.sink, "in2").eq(0)
            self.comb += getattr(source, name + "f").eq(getattr(self.datapath.source, "out"))

        self.latency = self.datapath.latency
