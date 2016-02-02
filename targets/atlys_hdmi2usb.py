from targets.common import *
from targets.atlys_base import *
from targets.atlys_base import default_subtarget as BaseSoC

from gateware.hdmi_in import HDMIIn
from gateware.hdmi_out import HDMIOut
from gateware.encoder import Encoder
from gateware.encoder.dma import EncoderDMAReader
from gateware.encoder.buffer import EncoderBuffer
from gateware.streamer import USBStreamer
from migen.actorlib.fifo import AsyncFIFO, SyncFIFO
from migen.flow.actor import *

class VideomixerSoC(BaseSoC):
    csr_peripherals = (
        "hdmi_out0",
        "hdmi_out1",
        "hdmi_in0",
        "hdmi_in0_edid_mem",
        "hdmi_in1",
        "hdmi_in1_edid_mem",
    )
    csr_map_update(BaseSoC.csr_map, csr_peripherals)

    interrupt_map = {
        "hdmi_in0": 3,
        "hdmi_in1": 4,
    }
    interrupt_map.update(BaseSoC.interrupt_map)

    def __init__(self, platform, **kwargs):
        BaseSoC.__init__(self, platform, **kwargs)
        self.submodules.hdmi_in0 = HDMIIn(platform.request("hdmi_in", 0),
                                          self.sdram.crossbar.get_master(),
                                          fifo_depth=1024)
        self.submodules.hdmi_in1 = HDMIIn(platform.request("hdmi_in", 1),
                                          self.sdram.crossbar.get_master(),
                                          fifo_depth=1024)
        self.submodules.hdmi_out0 = HDMIOut(platform.request("hdmi_out", 0),
                                            self.sdram.crossbar.get_master())
        self.submodules.hdmi_out1 = HDMIOut(platform.request("hdmi_out", 1),
                                            self.sdram.crossbar.get_master(),
                                            self.hdmi_out0.driver.clocking) # share clocking with hdmi_out0
                                                                            # since no PLL_ADV left.

        platform.add_platform_command("""INST PLL_ADV LOC=PLL_ADV_X0Y0;""") # all PLL_ADV are used: router needs help...
        platform.add_platform_command("""PIN "hdmi_out_pix_bufg.O" CLOCK_DEDICATED_ROUTE = FALSE;""")
        platform.add_platform_command("""PIN "hdmi_out_pix_bufg_1.O" CLOCK_DEDICATED_ROUTE = FALSE;""")
        platform.add_platform_command("""
NET "{pix0_clk}" TNM_NET = "GRPpix0_clk";
NET "{pix1_clk}" TNM_NET = "GRPpix1_clk";
TIMESPEC "TSise_sucks7" = FROM "GRPpix0_clk" TO "GRPsys_clk" TIG;
TIMESPEC "TSise_sucks8" = FROM "GRPsys_clk" TO "GRPpix0_clk" TIG;
TIMESPEC "TSise_sucks9" = FROM "GRPpix1_clk" TO "GRPsys_clk" TIG;
TIMESPEC "TSise_sucks10" = FROM "GRPsys_clk" TO "GRPpix1_clk" TIG;
""", pix0_clk=self.hdmi_out0.driver.clocking.cd_pix.clk,
     pix1_clk=self.hdmi_out1.driver.clocking.cd_pix.clk,
)
        for k, v in platform.hdmi_infos.items():
            self.add_constant(k, v)

class HDMI2USBSoC(VideomixerSoC):
    csr_peripherals = (
        "encoder_reader",
        "encoder",
    )
    csr_map_update(VideomixerSoC.csr_map, csr_peripherals)
    mem_map = {
        "encoder": 0x50000000,  # (shadow @0xd0000000)
    }
    mem_map.update(VideomixerSoC.mem_map)

    def __init__(self, platform, **kwargs):
        VideomixerSoC.__init__(self, platform, **kwargs)

        lasmim = self.sdram.crossbar.get_master()
        self.submodules.encoder_reader = EncoderDMAReader(lasmim)
        self.submodules.encoder_cdc = RenameClockDomains(AsyncFIFO([("data", 128)], 4),
                                          {"write": "sys", "read": "encoder"})
        self.submodules.encoder_buffer = RenameClockDomains(EncoderBuffer(), "encoder")
        self.submodules.encoder_fifo = RenameClockDomains(SyncFIFO(EndpointDescription([("data", 16)], packetized=True), 16), "encoder")
        self.submodules.encoder = Encoder(platform)
        self.submodules.usb_streamer = USBStreamer(platform, platform.request("fx2"))

        self.comb += [
            platform.request("user_led", 0).eq(self.encoder_reader.source.stb),
            platform.request("user_led", 1).eq(self.encoder_reader.source.ack),
            Record.connect(self.encoder_reader.source, self.encoder_cdc.sink),
            Record.connect(self.encoder_cdc.source, self.encoder_buffer.sink),
            Record.connect(self.encoder_buffer.source, self.encoder_fifo.sink),
            Record.connect(self.encoder_fifo.source, self.encoder.sink),
            Record.connect(self.encoder.source, self.usb_streamer.sink)
        ]
        self.add_wb_slave(mem_decoder(self.mem_map["encoder"]), self.encoder.bus)
        self.add_memory_region("encoder", self.mem_map["encoder"]+self.shadow_base, 0x2000)

        platform.add_platform_command("""
NET "{usb_clk}" TNM_NET = "GRPusb_clk";
TIMESPEC "TSise_sucks11" = FROM "GRPusb_clk" TO "GRPsys_clk" TIG;
TIMESPEC "TSise_sucks12" = FROM "GRPsys_clk" TO "GRPusb_clk" TIG;
""", usb_clk=platform.lookup_request("fx2").ifclk)

default_subtarget = HDMI2USBSoC
