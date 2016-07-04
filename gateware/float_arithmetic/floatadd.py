# floatadd

from migen.fhdl.std import *
from migen.genlib.record import *
from migen.bank.description import *
from migen.flow.actor import *

from gateware.float_arithmetic.common import *

datapath_latency = 5

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
        # (Equation from XAPP930)
        #    y = ca*(r-g) + g + cb*(b-g) + yoffset
        #   cb = cc*(r-y) + coffset
        #   cr = cd*(b-y) + coffset

        # stage 1
        # Unpack
        # Look for special cases

        a_frac = Signal(10)
        b_frac = Signal(10)
        
        a_mant = Signal(11)
        b_mant = Signal(11)

        a_exp = Signal(5)
        b_exp = Signal(5)

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

        self.sync += [

            a_stage1.eq(sink.a),
            b_stage1.eq(15362),

            If( a_exp==0,
                a_mant.eq( Cat(a_frac, 0)),     
                a_exp1.eq(a_exp + 1 )       
            ).Else(
                a_mant.eq( Cat(a_frac, 1)),
                a_exp1.eq(a_exp)
            ),

            If( b_exp==0,
                b_mant.eq( Cat(b_frac, 0)),     
                b_exp1.eq(b_exp + 1 )       
            ).Else(
                b_mant.eq( Cat(b_frac, 1)),
                b_exp1.eq(b_exp)
            ),  


            c_status1.eq(3),

        ]

        # stage 2
        # Multiply fractions and add exponents

        c_mult = Signal(22)
        c_exp = Signal((7,True))
        c_status2 = Signal(2)        
        var2 = Signal(22)
        a_stage2 = Signal(16)
        b_stage2 = Signal(16)

        self.sync += [
            a_stage2.eq(a_stage1),
            b_stage2.eq(b_stage1),

            c_mult.eq(a_mant * b_mant),
            c_exp.eq(a_exp1 + b_exp1 - 15),
            c_status2.eq(c_status1),
#            var2.eq(a_exp1)

        ]

        # stage 3
        # Leading one detector
        one_ptr = Signal(5) 
        c_status3 = Signal(2)
        c_mult3 = Signal(22)
        c_exp3 = Signal((7,True))
        var3 = Signal(22)
        a_stage3 = Signal(16)
        b_stage3 = Signal(16)

        self.sync += [
            a_stage3.eq(a_stage2),
            b_stage3.eq(b_stage2),
            c_status3.eq(c_status2),
            c_mult3.eq(c_mult),
            c_exp3.eq(c_exp),
            var3.eq(c_mult[6:]),

            If( c_mult[21]==1,
                one_ptr.eq(0)
            ).Elif(c_mult[20] == 1,
                one_ptr.eq(1)
            ).Elif(c_mult[19] == 1,
                one_ptr.eq(2)
            ).Elif(c_mult[18] == 1,
                one_ptr.eq(3)
            ).Elif(c_mult[17] == 1,
                one_ptr.eq(4)
            ).Elif(c_mult[16] == 1,
                one_ptr.eq(5)
            ).Elif(c_mult[15] == 1,
                one_ptr.eq(6)
            ).Elif(c_mult[14] == 1,
                one_ptr.eq(7)
            ).Elif(c_mult[13] == 1,
                one_ptr.eq(8)
            ).Elif(c_mult[12] == 1,
                one_ptr.eq(9)
            ).Elif(c_mult[11] == 1,
                one_ptr.eq(10)
            ).Elif(c_mult[10] == 1,
                one_ptr.eq(11)
            ).Elif(c_mult[ 9] == 1,
                one_ptr.eq(12)
            ).Elif(c_mult[ 8] == 1,
                one_ptr.eq(13)
            ).Elif(c_mult[ 7] == 1,
                one_ptr.eq(14)
            ).Elif(c_mult[ 6] == 1,
                one_ptr.eq(15)
            ).Elif(c_mult[ 5] == 1,
                one_ptr.eq(16)
            ).Elif(c_mult[ 4] == 1,
                one_ptr.eq(17)
            ).Elif(c_mult[ 3] == 1,
                one_ptr.eq(18)
            ).Elif(c_mult[ 2] == 1,
                one_ptr.eq(19)
            ).Elif(c_mult[ 1] == 1,
                one_ptr.eq(20)
            )

        ]

        # stage 4
        # Shift and Adjust
        c_exp_adjust = Signal((7,True))
        c_mult_shift = Signal(22)
        c_status4 = Signal(2)
        var4 = Signal(3)        
        a_stage4 = Signal(16)
        b_stage4 = Signal(16)

        self.sync += [
            a_stage4.eq(a_stage3),
            b_stage4.eq(64),

            c_status4.eq(c_status3),

            If( (c_exp3 - one_ptr) < 1,

                c_exp_adjust.eq(0),
                c_mult_shift.eq( ( (c_mult >> (0-c_exp3)) << 1) )

            ).Else(
                c_exp_adjust.eq(c_exp3 +1 - one_ptr),
                c_mult_shift.eq(c_mult << one_ptr+1 )

            ),
            # if c_exp3+1-one_ptr > 1 do standard
            # else c_mult = c_mult<<1
            #c_exp_adjust.eq(c_exp3 + 1 - (one_ptr) ),
            #c_mult_shift.eq(c_mult << one_ptr+1),
            var4.eq(0)

        ]

        # stage 5
        # Normalize and pack
        self.sync += [
        #    If(c_status4 == 3,
        #        source.c.eq( Cat(c_mult_shift[12:], c_exp_adjust[:5],0) )
        #    ),
            source.c.eq(a_stage4+b_stage4)

        ]


class FloatAdd(PipelinedActor, Module, AutoCSR):
    def __init__(self, dw=16):
        self.sink = sink = Sink(EndpointDescription(in_layout(dw), packetized=True))
        self.source = source = Source(EndpointDescription(out_layout(dw), packetized=True))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

        self._float_in1 = CSRStorage(dw)
        self._float_in2 = CSRStorage(dw)
        self._float_out = CSRStatus(dw)

        self.comb += [
            self._float_in1.storage.eq(getattr(sink, "a")),
            self._float_in2.storage.eq(getattr(sink, "b")),
            self._float_out.status.eq(getattr(source, "c"))
        ]

        self.submodules.datapath = FloatAddDatapath(dw)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        for name in ["a", "b"]:
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))
        self.comb += getattr(source, "c").eq(getattr(self.datapath.source, "c"))
