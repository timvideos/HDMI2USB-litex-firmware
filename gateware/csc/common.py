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


def coef(value, cw=None):
    return int(value * 2**cw) if cw is not None else value

def rgb16f_coefs():
    float16_offset = 15     # 01111
    float16_exp_len = 5
    float16_frac_len = 10

    return {
    float16_offset,
    float16_exp_len,
    float16_frac_len
    }

def rgb_layout(dw):
    return [("r", dw), ("g", dw), ("b", dw)]

def rgb16f_layout(dw):
    return [("r_f", dw), ("g_f", dw), ("b_f", dw)]

def ycbcr444_layout(dw):
    return [("y", dw), ("cb", dw), ("cr", dw)]

def ycbcr422_layout(dw):
    return [("y", dw), ("cb_cr", dw)]
