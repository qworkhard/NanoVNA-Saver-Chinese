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
import logging
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from ..Analysis.AntennaAnalysis import MagLoopAnalysis
from ..Analysis.BandPassAnalysis import BandPassAnalysis
from ..Analysis.BandStopAnalysis import BandStopAnalysis
from ..Analysis.Base import Analysis
from ..Analysis.EFHWAnalysis import EFHWAnalysis
from ..Analysis.HighPassAnalysis import HighPassAnalysis
from ..Analysis.LowPassAnalysis import LowPassAnalysis
from ..Analysis.PeakSearchAnalysis import PeakSearchAnalysis
from ..Analysis.ResonanceAnalysis import ResonanceAnalysis
from ..Analysis.SimplePeakSearchAnalysis import (
    SimplePeakSearchAnalysis,
)
from ..Analysis.VSWRAnalysis import VSWRAnalysis
from ..Windows.Defaults import make_scrollable
from .ui import get_window_icon

if TYPE_CHECKING:
    from ..NanoVNASaver.NanoVNASaver import NanoVNASaver as vna_app

logger = logging.getLogger(__name__)


class AnalysisWindow(QtWidgets.QWidget):
    analysis: Analysis | None = None

    def __init__(self, app: "vna_app"):
        super().__init__()

        self.app = app
        self.setWindowTitle("扫频数据分析")
        self.setWindowIcon(get_window_icon())

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, layout)

        select_analysis_box = QtWidgets.QGroupBox("选择分析模式")
        select_analysis_layout = QtWidgets.QFormLayout(select_analysis_box)
        self.analysis_list = QtWidgets.QComboBox()
        self.analysis_list.addItem("低通滤波器 (Low-pass)", LowPassAnalysis(self.app))
        self.analysis_list.addItem(
            "带通滤波器 (Band-pass)", BandPassAnalysis(self.app)
        )
        self.analysis_list.addItem(
            "高通滤波器 (High-pass)", HighPassAnalysis(self.app)
        )
        self.analysis_list.addItem(
            "带阻滤波器 (Band-stop)", BandStopAnalysis(self.app)
        )
        self.analysis_list.addItem(
            "简易峰值搜索", SimplePeakSearchAnalysis(self.app)
        )
        self.analysis_list.addItem("峰值搜索", PeakSearchAnalysis(self.app))
        self.analysis_list.addItem("VSWR 驻波比分析", VSWRAnalysis(self.app))
        self.analysis_list.addItem(
            "谐振点分析", ResonanceAnalysis(self.app)
        )
        self.analysis_list.addItem("半波端馈分析 (EFHW)", EFHWAnalysis(self.app))
        self.analysis_list.addItem(
            "小环天线分析 (MagLoop)", MagLoopAnalysis(self.app)
        )
        select_analysis_layout.addRow("分析类型", self.analysis_list)
        self.analysis_list.currentIndexChanged.connect(self.updateSelection)

        btn_run_analysis = QtWidgets.QPushButton("执行分析")
        btn_run_analysis.clicked.connect(self.runAnalysis)
        select_analysis_layout.addRow(btn_run_analysis)

        self.checkbox_run_automatically = QtWidgets.QCheckBox(
            "自动执行分析"
        )
        self.checkbox_run_automatically.stateChanged.connect(
            self.toggleAutomaticRun
        )
        select_analysis_layout.addRow(self.checkbox_run_automatically)

        analysis_box = QtWidgets.QGroupBox("分析结果")
        analysis_box.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        self.analysis_layout = QtWidgets.QVBoxLayout(analysis_box)
        self.analysis_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(select_analysis_box)
        layout.addWidget(analysis_box)

        self.updateSelection()

    def runAnalysis(self):
        if self.analysis is not None:
            self.analysis.runAnalysis()

    def updateSelection(self):
        self.analysis = self.analysis_list.currentData()
        old_item = self.analysis_layout.itemAt(0)
        if old_item is not None:
            old_widget = self.analysis_layout.itemAt(0).widget()
            self.analysis_layout.replaceWidget(
                old_widget, self.analysis.widget()
            )
            old_widget.hide()
        else:
            self.analysis_layout.addWidget(self.analysis.widget())
        self.analysis.widget().show()
        self.update()

    def toggleAutomaticRun(self, state: Qt.CheckState):
        if state == Qt.CheckState.Checked.value:
            self.analysis_list.setDisabled(True)
            self.app.communicate.data_available.connect(self.runAnalysis)
        else:
            self.analysis_list.setDisabled(False)
            self.app.communicate.data_available.disconnect(self.runAnalysis)
