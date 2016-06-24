from migen.fhdl.std import *
from migen.fhdl import verilog


class FloatMult(Module):
    def __init__(self):
        a = Signal(16)
        b = Signal(16)
        z = Signal(16)

        a_f = Signal(11)
        b_f = Signal(11)
        z_e = Signal((7, True))

        z_exp = Signal(5)
        z_fra = Signal(10)
        z_fra_shifted = Signal(10)
        z_exp_shifted = Signal(5)
        z_mult = Signal(22)

        #Stage1
        self.sync += [
            z_e.eq( a[10:15] + b[10:15] -15 ),
            a_f.eq( Cat(a[0:10], 1)),
            b_f.eq( Cat(b[0:10], 1)),
        ]

        If(z_e<=0, 
            z_exp.eq(0), 
            z_fra.eq(0)
        )Elif(z_e<32, 
            z_exp.eq(z_e)
        )Else(
            z_exp.eq(31), 
            z_fra(0)
        )

        #Stage2
        self.sync += [ 
            z_fra.eq( a[10:15] + b[10:15] -15 ) ,
            z_mult.eq( a_f*b_f ) ,
        ]

#       leading one detector, lshift value
#       Define a Module for this later

        #Stage3
        self.sync += [ 
            z_fra_shifted.eq( (z_mult << lshift+1)[:10] ) ,
            z_exp_shifted.eq(z_exp - lshift )
        ]


print(verilog.convert(FloatMult()))
