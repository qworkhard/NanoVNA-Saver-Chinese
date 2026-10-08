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

from ..RFTools import Datapoint
from ..Touchstone import Touchstone
from .Defaults import make_scrollable
from .ui import get_window_icon

if TYPE_CHECKING:
    from ..NanoVNASaver.NanoVNASaver import NanoVNASaver as vna_app
logger = logging.getLogger(__name__)


class FilesWindow(QtWidgets.QWidget):
    def __init__(self, app: "vna_app"):
        super().__init__()
        self.app = app

        self.setWindowTitle("文件导入与导出")
        self.setWindowIcon(get_window_icon())
        self.setMinimumWidth(200)
        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        file_window_layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, file_window_layout)

        load_file_control_box = QtWidgets.QGroupBox("导入文件")
        load_file_control_box.setMaximumWidth(300)
        load_file_control_layout = QtWidgets.QFormLayout(load_file_control_box)

        btn_load_sweep = QtWidgets.QPushButton("作为扫频数据加载")
        btn_load_sweep.clicked.connect(self.loadSweepFile)
        btn_load_reference = QtWidgets.QPushButton("加载参考基准数据")
        btn_load_reference.clicked.connect(self.loadReferenceFile)
        load_file_control_layout.addRow(btn_load_sweep)
        load_file_control_layout.addRow(btn_load_reference)

        file_window_layout.addWidget(load_file_control_box)

        save_file_control_box = QtWidgets.QGroupBox("导出文件")
        save_file_control_box.setMaximumWidth(300)
        save_file_control_layout = QtWidgets.QFormLayout(save_file_control_box)

        btn_export_file = QtWidgets.QPushButton("保存单端口文件 (.s1p)")
        btn_export_file.clicked.connect(lambda: self.exportFile(1))
        save_file_control_layout.addRow(btn_export_file)

        btn_export_file = QtWidgets.QPushButton("保存双端口文件 (.s2p)")
        btn_export_file.clicked.connect(lambda: self.exportFile(4))
        save_file_control_layout.addRow(btn_export_file)

        file_window_layout.addWidget(save_file_control_box)

        btn_open_file_window = QtWidgets.QPushButton("文件 ...")
        btn_open_file_window.clicked.connect(
            lambda: self.app.display_window("file")
        )

    def exportFile(self, nr_params: int = 1):
        if len(self.app.data.s11) == 0:
            QtWidgets.QMessageBox.warning(
                self, "无数据可保存", "当前没有可保存的测量数据。"
            )
            return
        if nr_params > 2 and len(self.app.data.s21) == 0:
            QtWidgets.QMessageBox.warning(
                self, "无 S21 数据", "当前没有可保存的 S21 数据。"
            )
            return

        filedialog = QtWidgets.QFileDialog(self)
        if nr_params == 1:
            filedialog.setDefaultSuffix("s1p")
            filedialog.setNameFilter(
                "Touchstone 单端口文件 (*.s1p);;所有文件 (*.*)"
            )
        else:
            filedialog.setDefaultSuffix("s2p")
            filedialog.setNameFilter(
                "Touchstone 双端口文件 (*.s2p);;所有文件 (*.*)"
            )
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        selected = filedialog.exec()
        if not selected:
            return
        filename = filedialog.selectedFiles()[0]
        if filename == "":
            logger.debug("No file name selected.")
            return

        ts = Touchstone(filename)
        ts.sdata[0] = self.app.data.s11
        if nr_params > 1:
            ts.sdata[1] = self.app.data.s21
            for dp in self.app.data.s11:
                ts.sdata[2].append(Datapoint(dp.freq, 0, 0))
                ts.sdata[3].append(Datapoint(dp.freq, 0, 0))
        try:
            ts.save(nr_params)
        except IOError as e:
            logger.exception("Error during file export: %s", e)
            return

    def loadReferenceFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Touchstone 文件 (*.s1p *.s2p);;所有文件 (*.*)"
        )
        if filename != "":
            self.app.resetReference()
            t = Touchstone(filename)
            t.load()
            self.app.setReference(t.s11, t.s21, filename)

    def loadSweepFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Touchstone 文件 (*.s1p *.s2p);;所有文件 (*.*)"
        )
        if filename != "":
            self.app.data.s11 = []
            self.app.data.s21 = []
            t = Touchstone(filename)
            t.load()
            self.app.saveData(t.s11, t.s21, filename)
            self.app.dataUpdated()
