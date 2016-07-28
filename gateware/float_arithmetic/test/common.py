from PIL import Image

import random
import copy
import numpy as np


from migen.fhdl.std import *
from migen.flow.actor import Sink, Source
from migen.genlib.record import *


def seed_to_data(seed, random=True):
    if random:
        return (seed * 0x31415979 + 1) & 0xffffffff
    else:
        return seed


def comp(p1, p2):
    r = True
    for x, y in zip(p1, p2):
        if x != y:
            r = False
    return r


def check(p1, p2):
    p1 = copy.deepcopy(p1)
    p2 = copy.deepcopy(p2)
    if isinstance(p1, int):
        return 0, 1, int(p1 != p2)
    else:
        if len(p1) >= len(p2):
            ref, res = p1, p2
        else:
            ref, res = p2, p1
        shift = 0
        while((ref[0] != res[0]) and (len(res) > 1)):
            res.pop(0)
            shift += 1
        length = min(len(ref), len(res))
        errors = 0
        for i in range(length):
            if ref.pop(0) != res.pop(0):
                errors += 1
        return shift, length, errors


def randn(max_n):
    return random.randint(0, max_n-1)


class Packet(list):
    def __init__(self, init=[]):
        self.ongoing = False
        self.done = False
        for data in init:
            self.append(data)


class PacketStreamer(Module):
    def __init__(self, description, last_be=None):
        self.source = Source(description)
        self.last_be = last_be

        # # #

        self.packets = []
        self.packet = Packet()
        self.packet.done = True

    def send(self, packet):
        packet = copy.deepcopy(packet)
        self.packets.append(packet)
        return packet

    def send_blocking(self, packet):
        packet = self.send(packet)
        while not packet.done:
            yield

    def do_simulation(self, selfp):
        if len(self.packets) and self.packet.done:
            self.packet = self.packets.pop(0)
        if not self.packet.ongoing and not self.packet.done:
            selfp.source.stb = 1
            if self.source.description.packetized:
                selfp.source.sop = 1
            selfp.source.data = self.packet.pop(0)
            self.packet.ongoing = True
        elif selfp.source.stb == 1 and selfp.source.ack == 1:
            if self.source.description.packetized:
                selfp.source.sop = 0
                if len(self.packet) == 1:
                    selfp.source.eop = 1
                    if self.last_be is not None:
                        selfp.source.last_be = self.last_be
                else:
                    selfp.source.eop = 0
                    if self.last_be is not None:
                        selfp.source.last_be = 0
            if len(self.packet) > 0:
                selfp.source.stb = 1
                selfp.source.data = self.packet.pop(0)
            else:
                self.packet.done = True
                selfp.source.stb = 0


class PacketLogger(Module):
    def __init__(self, description):
        self.sink = Sink(description)

        # # #

        self.packet = Packet()

    def receive(self):
        self.packet.done = False
        while not self.packet.done:
            yield

    def do_simulation(self, selfp):
        selfp.sink.ack = 1
        if selfp.sink.stb:
            if self.sink.description.packetized:
                if selfp.sink.sop:
                    self.packet = Packet()
                    self.packet.append(selfp.sink.data)
                else:
                    self.packet.append(selfp.sink.data)
                if selfp.sink.eop:
                    self.packet.done = True
            else:
                self.packet.append(selfp.sink.data)


class AckRandomizer(Module):
    def __init__(self, description, level=0):
        self.level = level

        self.sink = Sink(description)
        self.source = Source(description)

        self.run = Signal()

        self.comb += \
            If(self.run,
                Record.connect(self.sink, self.source)
            ).Else(
                self.source.stb.eq(0),
                self.sink.ack.eq(0),
            )

    def do_simulation(self, selfp):
        n = randn(100)
        if n < self.level:
            selfp.run = 0
        else:
            selfp.run = 1


class RAWImage:
    def __init__(self, coefs, filename=None, size=None):
        self.a = None
        self.b = None
        self.c = None

        self.data = []

        self.length = None

        self.open()


    def open(self):


        l1 = range(256)
        a = [float2binint(float(x)/256) for x in l1]        
#        a = [float2binint(float(1)/256) , float2binint(float(3)/256) , float2binint(float(7)/256)]
        b = [float2binint(0.0)]*256

        print ("Mult out" , float(4)/256)
        print( "Mult bin", bin(float2binint(float(4)/256))[2:].zfill(16) )
        self.set_mult_in(a, b)

    def set_mult_in(self, a, b):
        self.a = a
        self.b = b
        self.length = len(a)

    def set_data(self, data):
        self.data = data

    def pack_mult_in(self):
        self.data = []
        for i in range(self.length):
            data = (self.a[i] & 0xffff) << 16
            data |= (self.b[i] & 0xffff) << 0
            self.data.append(data)
        q = bin(data)[2:].zfill(32)
        return self.data

    def unpack_mult_in(self):
        self.c = []
        for data in self.data:
            self.c.append((data >> 0) & 0xffff)
        print("Output starts here")
        for i in range(len(self.c)):
            print(bin(self.c[i])[2:].zfill(16) )
            print(256*binint2float(self.c[i]))
            print()
            print(" ")

        return self.c


def float2binint(f):
    x = int(np.float16(f).view('H'))
    return x


def binint2float(x):
    xs = bin(x)[2:].zfill(16)
    frac = '1'+xs[6:16]
    fracn = int(frac,2)
    exp = xs[1:6]
    expn = int(exp,2) -15

    if expn == -15 :        #subnormal numbers
        expn = -14
        frac = '0'+xs[6:16]
        fracn = int(frac,2)

    sign = xs[0]
    signv = int(sign,2)

    y = ((-1)**signv)*(2**(expn))*fracn*(2**(-10))
    return y
