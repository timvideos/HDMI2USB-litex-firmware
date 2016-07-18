from migen.fhdl.std import *

def in_layout(dw):
    return [("in1", dw), ("in2", dw)]

def out_layout(dw):
    return [("out", dw)]
