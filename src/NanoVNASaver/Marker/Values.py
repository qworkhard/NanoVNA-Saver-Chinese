#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import NamedTuple

from ..RFTools import Datapoint


class Label(NamedTuple):
    label_id: str
    name: str
    description: str
    default_active: bool


TYPES = (
    Label("actualfreq", "频率", "实际测量频率", True),
    Label("lambda", "波长 (λ)", "工作波长", False),
    Label("impedance", "阻抗 (Z)", "复阻抗 R+jX", True),
    Label("admittance", "导纳 (Y)", "复导纳 G+jB", False),
    Label("serr", "串联电阻", "等效串联电阻", False),
    Label("serlc", "串联电抗", "等效串联电抗 L/C", False),
    Label("serl", "串联电感", "等效串联电感", True),
    Label("serc", "串联电容", "等效串联电容", True),
    Label("parr", "并联电阻", "等效并联电阻", True),
    Label("parlc", "并联电抗", "等效并联电抗 L/C", True),
    Label("parl", "并联电感", "等效并联电感", False),
    Label("parc", "并联电容", "等效并联电容", False),
    Label("vswr", "VSWR", "电压驻波比 (VSWR)", True),
    Label("returnloss", "Return Loss", "回波损耗 (Return Loss)", True),
    Label("s11mag", "|S11|", "S11 幅度", False),
    Label("s11q", "品质因数 Q", "S11 品质因数 (Q值)", True),
    Label("s11z", "S11 |Z|", "S11 阻抗模值", False),
    Label("s11phase", "S11 Phase", "S11 相位 (Phase)", True),
    Label("s11polar", "S11 Polar", "S11 极坐标 (Polar)", False),
    Label("s11groupdelay", "S11 Group Delay", "S11 群时延 (Group Delay)", False),
    Label("s21gain", "S21 Gain", "S21 增益 / 插入损耗", True),
    Label("s21mag", "|S21|", "S21 幅度", False),
    Label("s21phase", "S21 Phase", "S21 相位 (Phase)", True),
    Label("s21polar", "S21 Polar", "S21 极坐标 (Polar)", False),
    Label("s21groupdelay", "S21 Group Delay", "S21 群时延 (Group Delay)", False),
    Label("s21magshunt", "S21 |Z| 并联", "S21 并联阻抗模值", False),
    Label("s21magseries", "S21 |Z| 串联", "S21 串联阻抗模值", False),
    Label("s21realimagshunt", "S21 R+jX 并联", "S21 并联复阻抗", False),
    Label(
        "s21realimagseries", "S21 R+jX 串联", "S21 串联复阻抗", False
    ),
)


def default_label_ids() -> list[str]:
    return [label.label_id for label in TYPES if label.default_active]


class Value:
    """Contains the data area to calculate marker values from"""

    def __init__(self) -> None:
        self.freq: int = 0
        self.s11: list[Datapoint] = []
        self.s21: list[Datapoint] = []

    def store(self, index: int, s11: list[Datapoint], s21: list[Datapoint]):
        # handle boundaries
        if index == 0:
            index = 1
            s11 = [s11[0], *s11]
            if s21:
                s21 = [s21[0], *s21]
        if index == len(s11):
            s11 += [
                s11[-1],
            ]
            if s21:
                s21 += [
                    s21[-1],
                ]

        self.freq = s11[1].freq
        self.s11 = s11[index - 1 : index + 2]
        if s21:
            self.s21 = s21[index - 1 : index + 2]
