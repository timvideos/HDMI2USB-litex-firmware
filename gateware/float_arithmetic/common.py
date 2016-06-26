from migen.fhdl.std import *


def saturate(i, o, minimum, maximum):
    return [
        If(i > maximum,
            o.eq(maximum)
        ).Elif(i < minimum,
            o.eq(minimum)
        ).Else(
            o.eq(i)
        )
    ]

def in_layout(dw):
    return [("a", dw), ("b", dw)]

def out_layout(dw):
    return [("c", dw)]
