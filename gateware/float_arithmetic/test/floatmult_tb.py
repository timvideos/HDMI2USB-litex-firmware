from migen.fhdl.std import *
from migen.sim.generic import run_simulation
from migen.flow.actor import EndpointDescription

from gateware.float_arithmetic.common import *
from gateware.float_arithmetic.floatmult import FloatMult

from gateware.float_arithmetic.test.common import *


class TB(Module):
    def __init__(self):
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 32)], packetized=True))
        self.submodules.floatmult = FloatMult()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 16)], packetized=True))

        self.comb += [
        	Record.connect(self.streamer.source, self.floatmult.sink, leave_out=["data"]),
            self.floatmult.sink.payload.a.eq(self.streamer.source.data[16:32]),
            self.floatmult.sink.payload.b.eq(self.streamer.source.data[0:16]),

            Record.connect(self.floatmult.source, self.logger.sink, leave_out=["c"]),
            self.logger.sink.data[0:16].eq(self.floatmult.source.c)
        ]


    def gen_simulation(self, selfp):

        for i in range(16):
            yield

        # convert image using rgb2ycbcr implementation
        raw_image = RAWImage(None, None, 64)
        raw_image.pack_mult_in()
        packet = Packet(raw_image.data)
        self.streamer.send(packet)
        yield from self.logger.receive()
        raw_image.set_data(self.logger.packet)
        raw_image.unpack_mult_in()
#        raw_image.save("lena_rgb2ycbcr.png")

if __name__ == "__main__":
    run_simulation(TB(), ncycles=8192, vcd_name="my.vcd", keep_files=True)
