from gateware.i2c import I2C
from gateware.vga import VGAIn
from gateware.hdmi_in import HDMIIn
from gateware.hdmi_out import HDMIOut

from targets.common import *
from targets.atlys_base import BaseSoC as BaseSoC


def CreateVideoMixerSoC(base):

    class CustomVideoMixerSoC(base):
        csr_peripherals = (
            "i2c",
            "vga_in",
            "hdmi_out0",
            "hdmi_out1",
            "hdmi_in0",
            "hdmi_in0_edid_mem",
            "hdmi_in1",
            "hdmi_in1_edid_mem",
        )
        csr_map_update(base.csr_map, csr_peripherals)
    
        interrupt_map = {
            "vga_in"  : 2,
            "hdmi_in0": 3,
            "hdmi_in1": 4,
        }
        interrupt_map.update(base.interrupt_map)
    
        def __init__(self, platform, **kwargs):
            base.__init__(self, platform, **kwargs)
            vga_pads = platform.request("vga", 0)
            self.submodules.i2c = I2C(vga_pads)
            self.submodules.vga_in = VGAIn(
                vga_pads,
                self.sdram.crossbar.get_master(),
                fifo_depth=1024)
            self.submodules.hdmi_in0 = HDMIIn(
                platform.request("hdmi_in", 0),
                self.sdram.crossbar.get_master(),
                fifo_depth=1024)
            self.submodules.hdmi_in1 = HDMIIn(
                platform.request("hdmi_in", 1),
                self.sdram.crossbar.get_master(),
                fifo_depth=1024)
            self.submodules.hdmi_out0 = HDMIOut(
                platform.request("hdmi_out", 0),
                self.sdram.crossbar.get_master())
            # Share clocking with hdmi_out0 since no PLL_ADV left.
            self.submodules.hdmi_out1 = HDMIOut(
                platform.request("hdmi_out", 1),
                self.sdram.crossbar.get_master(),
                self.hdmi_out0.driver.clocking)
    
            # all PLL_ADV are used: router needs help...
            platform.add_platform_command("""INST PLL_ADV LOC=PLL_ADV_X0Y0;""")
            # FIXME: Fix the HDMI out so this can be removed.
            platform.add_platform_command(
                """PIN "hdmi_out_pix_bufg.O" CLOCK_DEDICATED_ROUTE = FALSE;""")
            platform.add_platform_command(
                """PIN "hdmi_out_pix_bufg_1.O" CLOCK_DEDICATED_ROUTE = FALSE;""")
            platform.add_platform_command(
                """
NET "{pix0_clk}" TNM_NET = "GRPpix0_clk";
NET "{pix1_clk}" TNM_NET = "GRPpix1_clk";
TIMESPEC "TSise_sucks7" = FROM "GRPpix0_clk" TO "GRPsys_clk" TIG;
TIMESPEC "TSise_sucks8" = FROM "GRPsys_clk" TO "GRPpix0_clk" TIG;
TIMESPEC "TSise_sucks9" = FROM "GRPpix1_clk" TO "GRPsys_clk" TIG;
TIMESPEC "TSise_sucks10" = FROM "GRPsys_clk" TO "GRPpix1_clk" TIG;
""", 
                pix0_clk=self.hdmi_out0.driver.clocking.cd_pix.clk,
                pix1_clk=self.hdmi_out1.driver.clocking.cd_pix.clk,
            )

            for k, v in sorted(platform.hdmi_infos.items()):
                self.add_constant(k, v)

    return CustomVideoMixerSoC


VideoMixerSoC = CreateVideoMixerSoC(BaseSoC)
default_subtarget = VideoMixerSoC
