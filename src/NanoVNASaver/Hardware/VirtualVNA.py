#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Virtual NanoVNA Simulation Driver for Educational and Testing Purposes
#
import logging
import math
from threading import RLock
from time import sleep
from typing import TYPE_CHECKING, Optional

import numpy as np
from PySide6 import QtGui

from ..utils import Version
from .Serial import Interface
from .VNA import VNA

if TYPE_CHECKING:
    from ..NanoVNASaver import NanoVNASaver

logger = logging.getLogger(__name__)


class VirtualInterface:
    def __init__(self):
        self.type = "serial"
        self.comment = "Virtual"
        self.port = "Virtual-NanoVNA"
        self.lock = RLock()
        self.is_open = True
        self.baudrate = 115200
        self.timeout = 0.05

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def isOpen(self) -> bool:
        return self.is_open

    def write(self, data: bytes) -> int:
        return len(data)

    def read(self, size: int = 1) -> bytes:
        return b""

    def readline(self) -> bytes:
        return b""

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass

    def __str__(self) -> str:
        return "Virtual NanoVNA (仿真)"


class VirtualVNA(VNA):
    name = "Virtual NanoVNA"
    screenwidth = 320
    screenheight = 240
    valid_datapoints = (101, 51, 11)
    sweep_points_max = 101
    sweep_points_min = 11
    sweep_max_freq_hz = 1500e6

    # 治具模式：AUTO（自动跟随校准向导），或手动固定为 DUT/SHORT/OPEN/LOAD/THRU
    current_fixture_mode = "AUTO"

    def __init__(self, iface):
        self.serial = iface
        self.version = Version.parse("0.7.3")
        self.features = {"Screenshots", "Bandwidth", "Customizable data points"}
        self.validateInput = False
        self.datapoints = 101
        self.bandwidth = 1000
        self.bw_method = "dislord"
        self.txPowerRanges = []
        self.start = 400000000
        self.stop = 600000000
        self.SN = "DEMO-001"
        self.app: Optional["NanoVNASaver"] = None
        logger.info("Virtual NanoVNA driver initialized")

    def read_fw_version(self) -> Version:
        return Version.parse("0.7.3")

    def init_features(self) -> None:
        self.features = {"Screenshots", "Bandwidth", "Customizable data points"}

    def set_app(self, app: "NanoVNASaver"):
        self.app = app

    def connected(self) -> bool:
        return getattr(self.serial, "is_open", True)

    def setSweep(self, start: int, stop: int):
        self.start = start
        self.stop = stop

    def resetSweep(self, start: int, stop: int):
        self.start = start
        self.stop = stop

    def read_frequencies(self) -> list[int]:
        return np.linspace(
            self.start, self.stop, self.datapoints, dtype=int
        ).tolist()

    def get_bandwidths(self) -> list[int]:
        return [1000, 2000, 4000]

    def set_bandwidth(self, bandwidth: int):
        self.bandwidth = bandwidth

    def getCalibration(self) -> str:
        return "虚拟演示固件"

    def getScreenshot(self) -> QtGui.QPixmap:
        pix = QtGui.QPixmap(320, 240)
        pix.fill(QtGui.QColor(20, 20, 30))
        painter = QtGui.QPainter(pix)
        painter.setPen(QtGui.QColor(0, 255, 128))
        painter.drawText(
            40, 120, "Virtual Device Demo"
        )
        painter.end()
        return pix

    def get_current_fixture(self) -> str:
        """识别当前应输出的标准件或待测物数据"""
        if self.current_fixture_mode != "AUTO":
            return self.current_fixture_mode

        # 自动探测校准向导步骤
        if self.app and "calibration" in getattr(self.app, "windows", {}):
            cal_win = self.app.windows["calibration"]
            step = getattr(cal_win, "next_step", -1)
            if step == 0:
                return "SHORT"
            if step == 1:
                return "OPEN"
            if step == 2:
                return "LOAD"
            if step == 3:
                return "THRU"
            if step == 4:
                return "ISOLATION"

        return "DUT"

    def readValues(self, value: str) -> list[complex]:
        freqs = self.read_frequencies()
        n = len(freqs)

        if value == "frequencies":
            return [complex(f, 0.0) for f in freqs]

        fixture = self.get_current_fixture()
        logger.info("Virtual VNA reading %s for fixture: %s", value, fixture)

        # 模拟真实硬件串口数据传输耗时（约 40ms，避免持续占用 CPU 导致 GUI 卡顿未响应）
        sleep(0.04)

        # 模拟 60cm 射频电缆相移 (延时约 5.5ns) 与 耦合器方向性泄漏 (-28dB)
        cable_delay = 5.5e-9

        if value == "data 0":  # S11 反射系数
            s11_list: list[complex] = []
            for f in freqs:
                phase_cable = -2.0 * math.pi * f * cable_delay
                cable_loss = 0.96  # 线缆微弱损耗
                directivity_leak = complex(0.03 * math.cos(f * 1e-7), 0.03 * math.sin(f * 1e-7))

                if fixture == "SHORT":
                    # 短路：Gamma 理想为 -1，加上线缆延时与损耗
                    gamma = -1.0 * cable_loss * complex(math.cos(phase_cable), math.sin(phase_cable))
                    s11_list.append(gamma + directivity_leak)

                elif fixture == "OPEN":
                    # 开路：Gamma 理想为 +1，加上线缆延时与损耗
                    gamma = +1.0 * cable_loss * complex(math.cos(phase_cable), math.sin(phase_cable))
                    s11_list.append(gamma + directivity_leak)

                elif fixture == "LOAD":
                    # 50 欧标准负载：极小反射 (<-40dB)
                    s11_list.append(directivity_leak + complex(0.003, -0.002))

                elif fixture == "THRU":
                    # 直通反射：端口良好匹配
                    s11_list.append(directivity_leak + complex(0.01, 0.005))

                elif fixture == "ISOLATION":
                    s11_list.append(directivity_leak)

                else:
                    # 默认待测物 (DUT): 一个在 500 MHz (或扫频中心) 谐振的天线
                    f_center = (self.start + self.stop) / 2.0
                    df = (f - f_center) / 30e6  # 30MHz 3dB带宽
                    # 谐振时 S11 深度达 -28 dB
                    # RLC 谐振反射模型
                    z_norm = complex(1.03, df)  # 归一化阻抗
                    gamma_dut = (z_norm - 1.0) / (z_norm + 1.0)
                    # 加上测试线缆引入的相移和定向耦合器误差
                    gamma_measured = directivity_leak + gamma_dut * cable_loss * complex(
                        math.cos(phase_cable), math.sin(phase_cable)
                    )
                    s11_list.append(gamma_measured)

            return s11_list

        elif value == "data 1":  # S21 传输系数
            s21_list: list[complex] = []
            for f in freqs:
                phase_cable = -2.0 * math.pi * f * cable_delay
                if fixture == "THRU":
                    # 直通：传输系数约 0.98 (-0.18 dB)
                    s21_list.append(0.98 * complex(math.cos(phase_cable), math.sin(phase_cable)))
                elif fixture in ("SHORT", "OPEN", "LOAD", "ISOLATION"):
                    # 隔离度/无直通：底噪 <-70dB
                    s21_list.append(complex(0.0002, 0.0001))
                else:
                    # DUT 传输：带通滤波器响应
                    f_center = (self.start + self.stop) / 2.0
                    df = abs(f - f_center) / 20e6
                    att_factor = 1.0 / (1.0 + (df ** 4))
                    s21_mag = 0.95 * att_factor + 0.001
                    s21_list.append(s21_mag * complex(math.cos(phase_cable), math.sin(phase_cable)))

            return s21_list

        return []
