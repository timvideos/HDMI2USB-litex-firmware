from migen.fhdl.std import *
from migen.sim.generic import run_simulation
from migen.flow.actor import EndpointDescription

from gateware.csc.common import *
from gateware.csc.rgb16f2rgb import rgb16f2rgb_coefs, RGB16f2RGB

from gateware.csc.test.common import *

class TB(Module):
    def __init__(self):
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 48)], packetized=True))
        self.submodules.rgb16f2rgb = RGB16f2RGB()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 24)], packetized=True))

        self.comb += [
            Record.connect(self.streamer.source, self.rgb16f2rgb.sink, leave_out=["data"]),
            self.rgb16f2rgb.sink.payload.y.eq(self.streamer.source.data[32:48]),
            self.rgb16f2rgb.sink.payload.cb.eq(self.streamer.source.data[16:32]),
            self.rgb16f2rgb.sink.payload.cr.eq(self.streamer.source.data[0:16]),

            Record.connect(self.rgb16f2rgb.source, self.logger.sink, leave_out=["r", "g", "b"]),
            self.logger.sink.data[16:24].eq(self.rgb16f2rgb.source.r),
            self.logger.sink.data[8:16].eq(self.rgb16f2rgb.source.g),
            self.logger.sink.data[0:8].eq(self.rgb16f2rgb.source.b)
        ]

    def gen_simulation(self, selfp):
        # convert image using rgb16f2rgb model
        raw_image = RAWImage(ycbcr2rgb_coefs(8), "lena.png", 64)
        raw_image.rgb2ycbcr()
        raw_image.ycbcr2rgb_model()
        raw_image.save("lena_ycbcr2rgb_reference.png")

        for i in range(16):
            yield

        # convert image using rgb16f2rgb implementation
        raw_image = RAWImage(ycbcr2rgb_coefs(8), "lena.png", 64)
        raw_image.rgb2rgb16f()
        raw_image.pack_rgb16f()
        packet = Packet(raw_image.data)
        self.streamer.send(packet)
        yield from self.logger.receive()
        raw_image.set_data(self.logger.packet)
        raw_image.unpack_rgb()
        raw_image.save("lena_rgb16f2rgb.png")


if __name__ == "__main__":
    run_simulation(TB(), ncycles=8192, vcd_name="my.vcd", keep_files=True)
