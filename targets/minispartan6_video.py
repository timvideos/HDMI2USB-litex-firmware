from migen.fhdl.std import ClockDomainsRenamer, ClockSignal, Signal, Instance

from gateware.hdmi_in import HDMIIn
from gateware.hdmi_in.edid import EDID
from gateware.hdmi_in.clocking import Clocking
from gateware.hdmi_in.datacapture import DataCapture
from gateware.hdmi_out import HDMIOut
from gateware import freq_count

from targets.common import *
from targets.minispartan6_base import default_subtarget as BaseSoC


class VideoMixerSoC(BaseSoC):
    csr_peripherals = (
        # "hdmi_out0",
        "edid",
        "edid_mem",
        "clocking",
        # "data0_cap",
        # "data0_cap",
        # "data0_cap"
        # "hdmi_in0",
        # "hdmi_in0_edid_mem",
    )
    csr_map_update(BaseSoC.csr_map, csr_peripherals)

    interrupt_map = {
        "hdmi_in0": 3,
    }
    interrupt_map.update(BaseSoC.interrupt_map)

    def __init__(self, platform, **kwargs):
        BaseSoC.__init__(self, platform, **kwargs)
        # self.submodules.hdmi_in0 = HDMIIn(
        #     platform.request("hdmi_in", 0),
        #     self.sdram.crossbar.get_master(),
        #     fifo_depth=1024)

        in_pads = platform.request("hdmi_in", 0)
        self.submodules.edid = EDID(in_pads)
        self.submodules.clocking = Clocking(in_pads)
        for datan in range(3):
            pad_se = Signal()
            name = "data" + str(datan)
            self.specials += Instance("IBUFDS", i_I=getattr(in_pads, name + "_p"),
                                      i_IB=getattr(in_pads, name + "_n"), o_O=pad_se)

        # self.submodules.hdmi_out0 = HDMIOut(
        #    platform.request("hdmi_out", 0),
        #    self.sdram.crossbar.get_master())

        # Only rename source, manually connect dest b/c of Migen decoration rules.
        # self.submodules.freq_count = ClockDomainsRenamer({"src" : "pix"})(freq_count.FrequencyCounter(80*1000000, 6, 32))
        self.submodules.freq_count = freq_count.FrequencyCounter(80*1000000, 6, 32)
        self.comb += [self.freq_count.core.cd_src.clk.eq(self.clocking._cd_pix.clk)]
        self.comb += [self.freq_count.core.cd_dest.clk.eq(self.crg.cd_sys.clk)]
        self.comb += [self.freq_count.core.cd_dest.rst.eq(self.crg.cd_sys.rst)]


        # FIXME: Fix the HDMI out so this can be removed.
#         platform.add_platform_command(
#             """PIN "hdmi_out_pix_bufg.O" CLOCK_DEDICATED_ROUTE = FALSE;""")
#         platform.add_platform_command(
#             """
# NET "{pix0_clk}" TNM_NET = "GRPpix0_clk";
# TIMESPEC "TSise_sucks7" = FROM "GRPpix0_clk" TO "GRPsys_clk" TIG;
# TIMESPEC "TSise_sucks8" = FROM "GRPsys_clk" TO "GRPpix0_clk" TIG;
# """,
#             pix0_clk=self.hdmi_out0.driver.clocking.cd_pix.clk,
#         )

        for k, v in sorted(platform.hdmi_infos.items()):
            self.add_constant(k, v)

default_subtarget = VideoMixerSoC
