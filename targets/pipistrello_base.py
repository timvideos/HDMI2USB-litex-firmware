# Support for the Pipistrello - http://pipistrello.saanlima.com/
from fractions import Fraction

from migen.fhdl.std import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.bus import wishbone

from misoclib.com import gpio
from misoclib.mem.flash import spiflash
from misoclib.mem.sdram.module import MT46H32M16
from misoclib.mem.sdram.phy import s6ddrphy
from misoclib.mem.sdram.core.lasmicon import LASMIconSettings
from misoclib.soc.sdram import SDRAMSoC

from gateware import dna
from gateware import firmware
from gateware import git_info
from gateware import hdmi_out
from gateware import i2c
from gateware import i2c_hack
from gateware import platform_info

from targets.common import *


class _CRG(Module):
    def __init__(self, platform, clk_freq):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_sdram_half = ClockDomain()
        self.clock_domains.cd_sdram_full_wr = ClockDomain()
        self.clock_domains.cd_sdram_full_rd = ClockDomain()
        self.clock_domains.cd_base50 = ClockDomain()
        self.clock_domains.cd_por = ClockDomain()

        self.clk4x_wr_strb = Signal()
        self.clk4x_rd_strb = Signal()

        f0 = Fraction(50, 1)*1000000
        p = 12
        f = Fraction(clk_freq*p, f0)
        n, d = f.numerator, f.denominator
        print("n/d : {}/{}".format(n ,d))
        assert 19e6 <= f0/d <= 500e6  # pfd
        assert 400e6 <= f0*n/d <= 1080e6  # vco

        clk50 = platform.request("clk50")
        clk50a = Signal()
        self.specials += Instance("IBUFG", i_I=clk50, o_O=clk50a)
        clk50b = Signal()
        self.specials += Instance("BUFIO2", p_DIVIDE=1,
                                  p_DIVIDE_BYPASS="TRUE", p_I_INVERT="FALSE",
                                  i_I=clk50a, o_DIVCLK=clk50b)
        pll_lckd = Signal()
        pll_fb = Signal()
        pll = Signal(6)
        self.specials.pll = Instance("PLL_ADV", p_SIM_DEVICE="SPARTAN6",
                                     p_BANDWIDTH="OPTIMIZED", p_COMPENSATION="INTERNAL",
                                     p_REF_JITTER=.01, p_CLK_FEEDBACK="CLKFBOUT",
                                     i_DADDR=0, i_DCLK=0, i_DEN=0, i_DI=0, i_DWE=0, i_RST=0, i_REL=0,
                                     p_DIVCLK_DIVIDE=d, p_CLKFBOUT_MULT=n, p_CLKFBOUT_PHASE=0.,
                                     i_CLKIN1=clk50b, i_CLKIN2=0, i_CLKINSEL=1,
                                     p_CLKIN1_PERIOD=1e9/f0, p_CLKIN2_PERIOD=0.,
                                     i_CLKFBIN=pll_fb, o_CLKFBOUT=pll_fb, o_LOCKED=pll_lckd,
                                     o_CLKOUT0=pll[0], p_CLKOUT0_DUTY_CYCLE=.5,
                                     o_CLKOUT1=pll[1], p_CLKOUT1_DUTY_CYCLE=.5,
                                     o_CLKOUT2=pll[2], p_CLKOUT2_DUTY_CYCLE=.5,
                                     o_CLKOUT3=pll[3], p_CLKOUT3_DUTY_CYCLE=.5,
                                     o_CLKOUT4=pll[4], p_CLKOUT4_DUTY_CYCLE=.5,
                                     o_CLKOUT5=pll[5], p_CLKOUT5_DUTY_CYCLE=.5,
                                     p_CLKOUT0_PHASE=0., p_CLKOUT0_DIVIDE=p//4,  # sdram wr rd
                                     p_CLKOUT1_PHASE=0., p_CLKOUT1_DIVIDE=p//4,
                                     p_CLKOUT2_PHASE=270., p_CLKOUT2_DIVIDE=p//2,  # sdram dqs adr ctrl
                                     p_CLKOUT3_PHASE=250., p_CLKOUT3_DIVIDE=p//2,  # off-chip ddr
                                     p_CLKOUT4_PHASE=0., p_CLKOUT4_DIVIDE=p//1,
                                     p_CLKOUT5_PHASE=0., p_CLKOUT5_DIVIDE=p//1,  # sys
        )
        self.specials += Instance("BUFG", i_I=pll[5], o_O=self.cd_sys.clk)
        reset = platform.request("user_btn")
        self.comb += self.cd_base50.clk.eq(clk50a)
        por = Signal(max=1 << 11, reset=(1 << 11) - 1)
        self.specials += AsyncResetSynchronizer(self.cd_base50, por > 0)
        self.sync.por += If(por != 0, por.eq(por - 1))
        self.comb += self.cd_por.clk.eq(self.cd_sys.clk)
        self.specials += AsyncResetSynchronizer(self.cd_por, reset)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~pll_lckd | (por > 0))
        self.specials += Instance("BUFG", i_I=pll[2], o_O=self.cd_sdram_half.clk)
        self.specials += Instance("BUFPLL", p_DIVIDE=4,
                                  i_PLLIN=pll[0], i_GCLK=self.cd_sys.clk,
                                  i_LOCKED=pll_lckd, o_IOCLK=self.cd_sdram_full_wr.clk,
                                  o_SERDESSTROBE=self.clk4x_wr_strb)
        self.comb += [
            self.cd_sdram_full_rd.clk.eq(self.cd_sdram_full_wr.clk),
            self.clk4x_rd_strb.eq(self.clk4x_wr_strb),
        ]
        clk_sdram_half_shifted = Signal()
        self.specials += Instance("BUFG", i_I=pll[3], o_O=clk_sdram_half_shifted)
        clk = platform.request("ddram_clock")
        self.specials += Instance("ODDR2", p_DDR_ALIGNMENT="NONE",
                                  p_INIT=0, p_SRTYPE="SYNC",
                                  i_D0=1, i_D1=0, i_S=0, i_R=0, i_CE=1,
                                  i_C0=clk_sdram_half_shifted, i_C1=~clk_sdram_half_shifted,
                                  o_Q=clk.p)
        self.specials += Instance("ODDR2", p_DDR_ALIGNMENT="NONE",
                                  p_INIT=0, p_SRTYPE="SYNC",
                                  i_D0=0, i_D1=1, i_S=0, i_R=0, i_CE=1,
                                  i_C0=clk_sdram_half_shifted, i_C1=~clk_sdram_half_shifted,
                                  o_Q=clk.n)


from mibuild.generic_platform import *
PipistrelloCustom = [
    ("fx2_hack", 0,
        Subsignal("scl", Pins("K12"), IOStandard("I2C"), Misc("PULLUP")), # WINGC 14
        Subsignal("sda", Pins("L12"), IOStandard("I2C"), Misc("PULLUP")), # WINGC 15
        IOStandard("I2C")
    ),
    ("fx2_reset", 0, Pins("K13"), IOStandard("LVCMOS33")), #, Misc("PULLUP")),
]


class BaseSoC(SDRAMSoC):
    default_platform = "pipistrello"

    csr_peripherals = (
        "spiflash",
        "ddrphy",
        "dna",
        "git_info",
        "platform_info",
        "fx2_reset",
        "fx2_hack",
    )
    csr_map_update(SDRAMSoC.csr_map, csr_peripherals)

    mem_map = {
        "firmware_ram": 0x20000000,  # (default shadow @0xa0000000)
        "spiflash": 0x30000000,  # (default shadow @0xb0000000)
    }
    mem_map.update(SDRAMSoC.mem_map)

    def __init__(self, platform,
                 firmware_ram_size=0xa000,
                 firmware_filename=None,
                 **kwargs):
        clk_freq = (83 + Fraction(1, 3))*1000*1000
        SDRAMSoC.__init__(self, platform, clk_freq,
                          cpu_type=os.environ.get("ARCH", "lm32"),
                          integrated_rom_size=0x8000,
                          sdram_controller_settings=LASMIconSettings(l2_size=32, with_bandwidth=True),
                          **kwargs)

        platform.add_extension(PipistrelloCustom)
        self.submodules.crg = _CRG(platform, clk_freq)
        self.submodules.dna = dna.DNA()
        self.submodules.git_info = git_info.GitInfo()
        self.submodules.platform_info = platform_info.PlatformInfo("pipistrello"[:8], self.__class__.__name__[:8])
        self.submodules.fx2_reset = gpio.GPIOOut(platform.request("fx2_reset"))
        self.submodules.fx2_hack = i2c_hack.I2CShiftReg(platform.request("fx2_hack"))

        self.submodules.firmware_ram = firmware.FirmwareROM(firmware_ram_size, firmware_filename)
        self.register_mem("firmware_ram", self.mem_map["firmware_ram"], self.firmware_ram.bus, firmware_ram_size)
        self.add_constant("ROM_BOOT_ADDRESS", self.mem_map["firmware_ram"])

        if not self.integrated_main_ram_size:
            self.submodules.ddrphy = s6ddrphy.S6HalfRateDDRPHY(platform.request("ddram"),
                                                               MT46H32M16(self.clk_freq),
                                                               rd_bitslip=1,
                                                               wr_bitslip=3,
                                                               dqs_ddr_alignment="C1")
            self.comb += [
                self.ddrphy.clk4x_wr_strb.eq(self.crg.clk4x_wr_strb),
                self.ddrphy.clk4x_rd_strb.eq(self.crg.clk4x_rd_strb),
            ]
            self.register_sdram_phy(self.ddrphy)

        self.submodules.spiflash = spiflash.SpiFlash(
            platform.request("spiflash4x"), dummy=platform.spiflash_read_dummy_bits, div=platform.spiflash_clock_div)
        self.add_constant("SPIFLASH_PAGE_SIZE", platform.spiflash_page_size)
        self.add_constant("SPIFLASH_SECTOR_SIZE", platform.spiflash_sector_size)
        self.flash_boot_address = self.mem_map["spiflash"]+platform.gateware_size
        self.register_mem("spiflash", self.mem_map["spiflash"], self.spiflash.bus, size=platform.gateware_size)


class VideomixerSoC(BaseSoC):

    csr_peripherals = (
        "hdmi_out0",
    )
    csr_map_update(BaseSoC.csr_map, csr_peripherals)

    def __init__(self, platform, **kwargs):
        BaseSoC.__init__(self, platform, **kwargs)
        self.submodules.hdmi_out0 = hdmi_out.HDMIOut(
            platform.request("hdmi", 0), self.sdram.crossbar.get_master())

        platform.add_platform_command("""PIN "hdmi_out_pix_bufg.O" CLOCK_DEDICATED_ROUTE = FALSE;""")

        for k, v in platform.hdmi_infos.items():
            self.add_constant(k, v)

default_subtarget = VideomixerSoC
