# floatadd

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
    def __init__(self,dw):
        self.sink = sink = Record(in_layout(dw))
        self.source = source = Record(out_layout(dw))

        # delay rgb signals
        in_delayed = [sink]
        for i in range(datapath_latency):
            in_n = Record(in_layout(dw))
            for name in ["a", "b"]:
                self.sync += getattr(in_n, name).eq(getattr(in_delayed[-1], name))
            in_delayed.append(in_n)

        # Hardware implementation:

        # stage 1
        # Unpack
        # Look for special cases
        # Substract Exponents

        a_frac = Signal(10)
        b_frac = Signal(10)
        
        a_mant = Signal(11)
        b_mant = Signal(11)

        a_exp = Signal(5)
        b_exp = Signal(5)

        a_minus_b_exp = Signal((6,True))

        a_exp1 = Signal(5)
        b_exp1 = Signal(5)

        a_sign = Signal()
        b_sign = Signal()


        c_status1 = Signal(2)
        # 00-0 Zero
        # 01-1 Inf
        # 10-2 Nan
        # 11-3 Normal 
        
        a_stage1 = Signal(16)
        b_stage1 = Signal(16)

        self.comb += [
            a_frac.eq( Cat(sink.a[:10], 1) ),
            b_frac.eq( Cat(sink.b[:10], 1) ),

            a_exp.eq( sink.a[10:15] ),
            b_exp.eq( sink.b[10:15] ),

            a_sign.eq( sink.a[15] ),
            b_sign.eq( sink.a[15] ),

        ]

        self.comb += [
            If( a_exp==0,
                a_mant.eq( Cat(a_frac, 0)),     
                a_exp1.eq( a_exp + 1 )       
            ).Else(
                a_mant.eq( Cat(a_frac, 1)),
                a_exp1.eq( a_exp)
            ),

            If( b_exp==0,
                b_mant.eq( Cat(b_frac, 0)),     
                b_exp1.eq(b_exp + 1 )       
            ).Else(
                b_mant.eq( Cat(b_frac, 1)),
                b_exp1.eq(b_exp)
            )
        ]

        a_frac_stage1 = Signal(11)
        b_frac_stage1 = Signal(11)
        a_sign_stage1 = Signal(11)
        b_sign_stage1 = Signal(11)
        a_exp_stage1 = Signal(5)
        b_exp_stage1 = Signal(5)

        self.sync += [

            a_minus_b_exp.eq(a_exp1 - b_exp),
            a_frac_stage1.eq(a_mant),	
            b_frac_stage1.eq(b_mant),	
            a_exp_stage1.eq(a_exp),   
            b_exp_stage1.eq(b_exp),   
            a_sign_stage1.eq(a_sign),
            b_sign_stage1.eq(b_sign),
            c_status1.eq(3),

        ]

        # stage 2
        # Adjust fracs to common exponent

        a_frac_stage2 = Signal(11)
        b_frac_stage2 = Signal(11)
        a_sign_stage2 = Signal(11)
        b_sign_stage2 = Signal(11)
        a_minus_b_exp_stage2 = Signal(5)
        out_2 = Signal(16)

        self.sync += [

            If( ~a_minus_b_exp[5], [
                b_frac_stage2.eq(b_frac_stage1 >> a_minus_b_exp),
                a_frac_stage2.eq(a_frac_stage1),
                a_minus_b_exp_stage2.eq(a_exp_stage1)
                ]
            ).Else ( [
#                out_2.eq(a_frac_stage1 >> (-1)*(-1)),
                a_frac_stage2.eq(a_frac_stage1 >> (-1)*a_minus_b_exp ),
                a_minus_b_exp_stage2.eq(b_exp_stage1),
                b_frac_stage2.eq(b_frac_stage1),
                ]
            ),
            a_sign_stage2.eq(a_sign_stage1),
            b_sign_stage2.eq(b_sign_stage1),
#            out_2.eq(a_frac_stage2)

        ]

        # stage 3
        # Adder Unit


        a_plus_b_frac = Signal(12)
        a_plus_b_sign = Signal(1)
        a_minus_b_exp_stage3 = Signal(5)
        out_3 = Signal(16)

        self.sync += [
            Cat(a_plus_b_frac, a_plus_b_sign).eq(a_frac_stage2+b_frac_stage2),
            a_minus_b_exp_stage3.eq(a_minus_b_exp_stage2),
            out_3.eq(out_2)
        ]

        # stage 4
        # Shift and Adjust

        leadone = Signal(4)
        self.submodules.l1 = LeadOne()
        
        self.comb += [
            self.l1.datai.eq(a_plus_b_frac),
            leadone.eq(self.l1.leadone)
        ]

        c_sign_stage4 = Signal(1)	
        c_frac_stage4 = Signal(12)	
        c_exp_stage4 = Signal(5)
        out_4 = Signal(16)

        self.sync += [
            c_frac_stage4.eq(a_plus_b_frac << (leadone)),
            c_exp_stage4.eq(a_minus_b_exp_stage3 - leadone + 1 ),
            c_sign_stage4.eq(a_plus_b_sign),
            out_4.eq(c_frac_stage4)
        ]

        # stage 5
        # Normalize and pack
        self.sync += [

#            source.c.eq( c_frac_stage4[1:11])
            source.c.eq( Cat( c_frac_stage4[1:11] , c_exp_stage4 ,c_sign_stage4 ) )
        ]


class FloatAdd(PipelinedActor, Module, AutoCSR):
    def __init__(self, dw=16):
        self.sink = sink = Sink(EndpointDescription(in_layout(dw), packetized=True))
        self.source = source = Source(EndpointDescription(out_layout(dw), packetized=True))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

        self.submodules.datapath = FloatAddDatapath(dw)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        for name in ["a", "b"]:
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))
        self.comb += getattr(source, "c").eq(getattr(self.datapath.source, "c"))
