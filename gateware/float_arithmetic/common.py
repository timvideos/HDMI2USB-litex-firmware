from migen.fhdl.std import *

def in_layout(dw):
    return [("in1", dw), ("in2", dw)]

def out_layout(dw):
    return [("out", dw)]

def rgb16f_layout(dw):
    return [("rf", dw), ("gf", dw), ("bf", dw)]

def rgb_layout(dw):
    return [("r", dw), ("g", dw), ("b", dw)]

def floatin_layout(dw):
    return [("r1", dw), ("g1", dw), ("b1", dw), ("r2", dw), ("g2", dw), ("b2", dw)]

