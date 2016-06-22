from migen.fhdl.std import *
from migen.sim.generic import run_simulation
from migen.flow.actor import EndpointDescription

from gateware.csc.common import *
from gateware.csc.rgb2rgb16f import RGB2RGB16f

from gateware.csc.test.common import *


class TB(Module):
    def __init__(self):
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 24)], packetized=True))
        self.submodules.rgb2rgb16f = RGB2RGB16f()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 48)], packetized=True))

        self.comb += [
        	Record.connect(self.streamer.source, self.rgb2rgb16f.sink, leave_out=["data"]),
            self.rgb2rgb16f.sink.payload.r.eq(self.streamer.source.data[16:24]),
            self.rgb2rgb16f.sink.payload.g.eq(self.streamer.source.data[8:16]),
            self.rgb2rgb16f.sink.payload.b.eq(self.streamer.source.data[0:8]),

            Record.connect(self.rgb2rgb16f.source, self.logger.sink, leave_out=["r_f", "g_f", "b_f"]),
            self.logger.sink.data[32:48].eq(self.rgb2rgb16f.source.r_f),
            self.logger.sink.data[16:32].eq(self.rgb2rgb16f.source.g_f),
            self.logger.sink.data[ 0:16].eq(self.rgb2rgb16f.source.b_f)
        ]


    def gen_simulation(self, selfp):
        # convert image using rgb2ycbcr model
        raw_image = RAWImage(rgb2ycbcr_coefs(8), "lena.png", 64)
        raw_image.rgb2ycbcr_model()
        raw_image.ycbcr2rgb()
        raw_image.save("lena_rgb2ycbcr_reference.png")

        for i in range(24):
            yield

        # convert image using rgb2ycbcr implementation
        raw_image = RAWImage(rgb2ycbcr_coefs(8), "lena.png", 64)
        raw_image.pack_rgb()
        packet = Packet(raw_image.data)
        self.streamer.send(packet)
        yield from self.logger.receive()
        raw_image.set_data(self.logger.packet)
        raw_image.unpack_rgb16f()
        raw_image.rgb16f2rgb()
        raw_image.save("lena_rgb2rgb16f.png")

if __name__ == "__main__":
    run_simulation(TB(), ncycles=8192, vcd_name="my.vcd", keep_files=True)
