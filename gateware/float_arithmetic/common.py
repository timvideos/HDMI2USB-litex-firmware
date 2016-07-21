from migen.fhdl.std import *

def in_layout(dw):
    return [("in1", dw), ("in2", dw)]

def out_layout(dw):
    return [("out", dw)]

def rgb16f_layout(dw):
    return [("rf", dw), ("gf", dw), ("bf", dw)]
