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
from functools import partial

from PySide6 import QtCore, QtGui, QtWidgets

from ..Calibration import Calibration
from ..Settings.Sweep import SweepMode
from ..Touchstone import Touchstone
from .Defaults import make_scrollable
from .ui import get_window_icon

logger = logging.getLogger(__name__)


def _format_cal_label(size: int, prefix: str = "已设置") -> str:
    return f"{prefix} ({size} 点)"


def getFloatValue(text: str) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


class CalibrationWindow(QtWidgets.QWidget):
    next_step = -1

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setMinimumWidth(450)
        self.setWindowTitle("校准")
        self.setWindowIcon(get_window_icon())
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        top_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()
        right_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout)

        make_scrollable(self, top_layout)

        calibration_status_group = QtWidgets.QGroupBox("当前有效校准")
        calibration_status_layout = QtWidgets.QFormLayout()
        self.calibration_status_label = QtWidgets.QLabel("设备硬件校准")
        self.calibration_source_label = QtWidgets.QLabel("NanoVNA")
        calibration_status_layout.addRow(
            "校准状态:", self.calibration_status_label
        )
        calibration_status_layout.addRow(
            "校准源:", self.calibration_source_label
        )
        calibration_status_group.setLayout(calibration_status_layout)
        left_layout.addWidget(calibration_status_group)

        calibration_control_group = QtWidgets.QGroupBox("校准采集")
        calibration_control_layout = QtWidgets.QFormLayout(
            calibration_control_group
        )
        cal_btn = {}
        self.cal_label = {}
        cal_btn_names = {
            "short": "短路 (Short)",
            "open": "开路 (Open)",
            "load": "负载 (Load)",
            "through": "直通 (Thru)",
            "thrurefl": "直通反射 (Thru Refl)",
            "isolation": "隔离度 (Isolation)",
        }
        for label_name in (
            "short",
            "open",
            "load",
            "through",
            "thrurefl",
            "isolation",
        ):
            self.cal_label[label_name] = QtWidgets.QLabel("未校准")
            cal_btn[label_name] = QtWidgets.QPushButton(
                cal_btn_names.get(label_name, label_name.capitalize())
            )
            cal_btn[label_name].setMinimumHeight(20)
            cal_btn[label_name].clicked.connect(
                partial(self.manual_save, label_name)
            )
            calibration_control_layout.addRow(
                cal_btn[label_name], self.cal_label[label_name]
            )

        self.input_offset_delay = QtWidgets.QDoubleSpinBox()
        self.input_offset_delay.setMinimumHeight(20)
        self.input_offset_delay.setValue(0)
        self.input_offset_delay.setSuffix(" ps")
        self.input_offset_delay.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.input_offset_delay.valueChanged.connect(self.setOffsetDelay)
        self.input_offset_delay.setRange(-10e6, 10e6)

        calibration_control_layout.addRow(QtWidgets.QLabel(""))
        calibration_control_layout.addRow(
            "偏置时延 (Offset Delay)", self.input_offset_delay
        )

        self.btn_automatic = QtWidgets.QPushButton("校准向导")
        self.btn_automatic.setMinimumHeight(20)
        calibration_control_layout.addRow(self.btn_automatic)
        self.btn_automatic.clicked.connect(self.automaticCalibration)

        apply_reset_layout = QtWidgets.QHBoxLayout()

        btn_apply = QtWidgets.QPushButton("应用")
        btn_apply.setMinimumHeight(20)
        btn_apply.clicked.connect(self.calculate)

        btn_reset = QtWidgets.QPushButton("复位")
        btn_reset.setMinimumHeight(20)
        btn_reset.clicked.connect(self.reset)

        apply_reset_layout.addWidget(btn_apply)
        apply_reset_layout.addWidget(btn_reset)

        calibration_control_layout.addRow(apply_reset_layout)

        left_layout.addWidget(calibration_control_group)

        calibration_notes_group = QtWidgets.QGroupBox("备注说明")
        calibration_notes_layout = QtWidgets.QVBoxLayout(
            calibration_notes_group
        )
        self.notes_textedit = QtWidgets.QPlainTextEdit()
        calibration_notes_layout.addWidget(self.notes_textedit)

        left_layout.addWidget(calibration_notes_group)

        file_box = QtWidgets.QGroupBox("校准文件")
        file_layout = QtWidgets.QFormLayout(file_box)
        btn_save_file = QtWidgets.QPushButton("保存校准")
        btn_save_file.setMinimumHeight(20)
        btn_save_file.clicked.connect(lambda: self.saveCalibration())
        btn_load_file = QtWidgets.QPushButton("加载校准")
        btn_load_file.setMinimumHeight(20)
        btn_load_file.clicked.connect(lambda: self.loadCalibration())

        save_load_layout = QtWidgets.QHBoxLayout()
        save_load_layout.addWidget(btn_save_file)
        save_load_layout.addWidget(btn_load_file)

        file_layout.addRow(save_load_layout)

        left_layout.addWidget(file_box)

        cal_standard_box = QtWidgets.QGroupBox("校准件标准 (Standards)")
        cal_standard_layout = QtWidgets.QFormLayout(cal_standard_box)
        self.use_ideal_values = QtWidgets.QRadioButton("使用理想值")
        self.use_s1p_files = QtWidgets.QRadioButton("使用 S1P 文件")
        self.use_coefficients = QtWidgets.QRadioButton("使用多项式系数")

        self.use_ideal_values.setChecked(True)
        self.radio_group = QtWidgets.QButtonGroup(self)
        self.radio_group.addButton(self.use_ideal_values)
        self.radio_group.addButton(self.use_s1p_files)
        self.radio_group.addButton(self.use_coefficients)
        self.radio_group.buttonClicked.connect(self.calStandardChanged)

        self.radio_layout = QtWidgets.QHBoxLayout()
        self.radio_layout.addWidget(self.use_ideal_values)
        self.radio_layout.addWidget(self.use_s1p_files)
        self.radio_layout.addWidget(self.use_coefficients)
        cal_standard_layout.addRow(self.radio_layout)

        self.file_button_short = QtWidgets.QPushButton("短路 (Short) S1P 文件")
        self.file_button_open = QtWidgets.QPushButton("开路 (Open) S1P 文件")
        self.file_button_load = QtWidgets.QPushButton("负载 (Load) S1P 文件")
        self.file_button_short.setEnabled(False)
        self.file_button_open.setEnabled(False)
        self.file_button_load.setEnabled(False)

        cal_standard_layout.addRow(self.file_button_short)
        cal_standard_layout.addRow(self.file_button_open)
        cal_standard_layout.addRow(self.file_button_load)

        self.file_button_open.clicked.connect(self.select_file_open)
        self.file_button_short.clicked.connect(self.select_file_short)
        self.file_button_load.clicked.connect(self.select_file_load)

        self.cal_short_box = QtWidgets.QGroupBox("短路 (Short)")
        cal_short_form = QtWidgets.QFormLayout(self.cal_short_box)
        self.cal_short_box.setDisabled(True)
        self.short_l0_input = QtWidgets.QLineEdit("0")
        self.short_l0_input.setMinimumHeight(20)
        self.short_l1_input = QtWidgets.QLineEdit("0")
        self.short_l1_input.setMinimumHeight(20)
        self.short_l2_input = QtWidgets.QLineEdit("0")
        self.short_l2_input.setMinimumHeight(20)
        self.short_l3_input = QtWidgets.QLineEdit("0")
        self.short_l3_input.setMinimumHeight(20)
        self.short_length = QtWidgets.QLineEdit("0")
        self.short_length.setMinimumHeight(20)
        cal_short_form.addRow("L0 (H(e-12))", self.short_l0_input)
        cal_short_form.addRow("L1 (H(e-24))", self.short_l1_input)
        cal_short_form.addRow("L2 (H(e-33))", self.short_l2_input)
        cal_short_form.addRow("L3 (H(e-42))", self.short_l3_input)
        cal_short_form.addRow("偏置时延 (Offset Delay) (ps)", self.short_length)

        self.cal_open_box = QtWidgets.QGroupBox("开路 (Open)")
        cal_open_form = QtWidgets.QFormLayout(self.cal_open_box)
        self.cal_open_box.setDisabled(True)
        self.open_c0_input = QtWidgets.QLineEdit("50")
        self.open_c0_input.setMinimumHeight(20)
        self.open_c1_input = QtWidgets.QLineEdit("0")
        self.open_c1_input.setMinimumHeight(20)
        self.open_c2_input = QtWidgets.QLineEdit("0")
        self.open_c2_input.setMinimumHeight(20)
        self.open_c3_input = QtWidgets.QLineEdit("0")
        self.open_c3_input.setMinimumHeight(20)
        self.open_length = QtWidgets.QLineEdit("0")
        self.open_length.setMinimumHeight(20)
        cal_open_form.addRow("C0 (F(e-15))", self.open_c0_input)
        cal_open_form.addRow("C1 (F(e-27))", self.open_c1_input)
        cal_open_form.addRow("C2 (F(e-36))", self.open_c2_input)
        cal_open_form.addRow("C3 (F(e-45))", self.open_c3_input)
        cal_open_form.addRow("偏置时延 (Offset Delay) (ps)", self.open_length)

        self.cal_load_box = QtWidgets.QGroupBox("负载 (Load)")
        cal_load_form = QtWidgets.QFormLayout(self.cal_load_box)
        self.cal_load_box.setDisabled(True)
        self.load_resistance = QtWidgets.QLineEdit("50")
        self.load_resistance.setMinimumHeight(20)
        self.load_inductance = QtWidgets.QLineEdit("0")
        self.load_inductance.setMinimumHeight(20)
        self.load_capacitance = QtWidgets.QLineEdit("0")
        self.load_capacitance.setMinimumHeight(20)
        # self.load_capacitance.setDisabled(True)  # Not yet implemented
        self.load_length = QtWidgets.QLineEdit("0")
        self.load_length.setMinimumHeight(20)
        cal_load_form.addRow("电阻 (Resistance) (\N{OHM SIGN})", self.load_resistance)
        cal_load_form.addRow("电感 (Inductance) (H(e-12))", self.load_inductance)
        cal_load_form.addRow("电容 (Capacitance) (F(e-15))", self.load_capacitance)
        cal_load_form.addRow("偏置时延 (Offset Delay) (ps)", self.load_length)

        self.cal_through_box = QtWidgets.QGroupBox("直通 (Thru)")
        cal_through_form = QtWidgets.QFormLayout(self.cal_through_box)
        self.cal_through_box.setDisabled(True)
        self.through_length = QtWidgets.QLineEdit("0")
        self.through_length.setMinimumHeight(20)
        cal_through_form.addRow("偏置时延 (Offset Delay) (ps)", self.through_length)

        cal_standard_layout.addWidget(self.cal_short_box)
        cal_standard_layout.addWidget(self.cal_open_box)
        cal_standard_layout.addWidget(self.cal_load_box)
        cal_standard_layout.addWidget(self.cal_through_box)

        self.cal_standard_save_box = QtWidgets.QGroupBox("已存校准件配置")
        cal_standard_save_layout = QtWidgets.QVBoxLayout(
            self.cal_standard_save_box
        )
        self.cal_standard_save_box.setDisabled(True)

        self.cal_standard_save_selector = QtWidgets.QComboBox()
        self.cal_standard_save_selector.setMinimumHeight(20)
        self.listCalibrationStandards()
        cal_standard_save_layout.addWidget(self.cal_standard_save_selector)
        cal_standard_save_button_layout = QtWidgets.QHBoxLayout()
        btn_save_standard = QtWidgets.QPushButton("保存")
        btn_save_standard.setMinimumHeight(20)
        btn_save_standard.clicked.connect(self.saveCalibrationStandard)
        btn_load_standard = QtWidgets.QPushButton("加载")
        btn_load_standard.setMinimumHeight(20)
        btn_load_standard.clicked.connect(self.loadCalibrationStandard)
        btn_delete_standard = QtWidgets.QPushButton("删除")
        btn_delete_standard.setMinimumHeight(20)
        btn_delete_standard.clicked.connect(self.deleteCalibrationStandard)
        cal_standard_save_button_layout.addWidget(btn_load_standard)
        cal_standard_save_button_layout.addWidget(btn_save_standard)
        cal_standard_save_button_layout.addWidget(btn_delete_standard)
        cal_standard_save_layout.addLayout(cal_standard_save_button_layout)

        cal_standard_layout.addWidget(self.cal_standard_save_box)
        right_layout.addWidget(cal_standard_box)
        self.open_touchstone = None
        self.short_touchstone = None
        self.load_touchstone = None

    def checkExpertUser(self):
        if not self.app.settings.value("ExpertCalibrationUser", False, bool):
            response = QtWidgets.QMessageBox.question(
                self,
                "Are you sure?",
                (
                    "Use of the manual calibration buttons is non-intuitive"
                    " and primarily suited for users with very specialized"
                    " needs. The buttons do not sweep for you nor do"
                    " they interact with the NanoVNA calibration.\n\n"
                    "If you are trying to do a calibration of the NanoVNA, do"
                    " so on the device itself instead. If you are trying to do"
                    ' a calibration with NanoVNA-Saver, use the "Calibration'
                    ' assistant" if possible.\n\n'
                    "If you are certain you know what you are doing, click"
                    " Yes."
                ),
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            if response == QtWidgets.QMessageBox.StandardButton.Yes:
                self.app.settings.setValue("ExpertCalibrationUser", True)
                return True
            return False
        return True

    def cal_save(self, name: str):
        if name in {"through", "isolation"}:
            self.app.calibration.insert(name, self.app.data.s21)
        else:
            self.app.calibration.insert(name, self.app.data.s11)
        self.cal_label[name].setText(_format_cal_label(len(self.app.data.s11)))

    def manual_save(self, name: str):
        if self.checkExpertUser():
            self.cal_save(name)

    def listCalibrationStandards(self):
        self.cal_standard_save_selector.clear()
        num_standards = self.app.settings.beginReadArray("CalibrationStandards")
        for i in range(num_standards):
            self.app.settings.setArrayIndex(i)
            name = self.app.settings.value("Name", defaultValue="INVALID NAME")
            self.cal_standard_save_selector.addItem(name, userData=i)
        self.app.settings.endArray()
        self.cal_standard_save_selector.addItem("New", userData=-1)
        self.cal_standard_save_selector.setCurrentText("New")

    def saveCalibrationStandard(self):
        num_standards = self.app.settings.beginReadArray("CalibrationStandards")
        self.app.settings.endArray()

        if self.cal_standard_save_selector.currentData() == -1:
            # New cal standard
            # Get a name
            name, selected = QtWidgets.QInputDialog.getText(
                self, "Calibration standard name", "Enter name to save as"
            )
            if not selected or not name:
                return
            write_num = num_standards
            num_standards += 1
        else:
            write_num = self.cal_standard_save_selector.currentData()
            name = self.cal_standard_save_selector.currentText()

        self.app.settings.beginWriteArray("CalibrationStandards", num_standards)
        self.app.settings.setArrayIndex(write_num)
        self.app.settings.setValue("Name", name)

        self.app.settings.setValue("ShortL0", self.short_l0_input.text())
        self.app.settings.setValue("ShortL1", self.short_l1_input.text())
        self.app.settings.setValue("ShortL2", self.short_l2_input.text())
        self.app.settings.setValue("ShortL3", self.short_l3_input.text())
        self.app.settings.setValue("ShortDelay", self.short_length.text())

        self.app.settings.setValue("OpenC0", self.open_c0_input.text())
        self.app.settings.setValue("OpenC1", self.open_c1_input.text())
        self.app.settings.setValue("OpenC2", self.open_c2_input.text())
        self.app.settings.setValue("OpenC3", self.open_c3_input.text())
        self.app.settings.setValue("OpenDelay", self.open_length.text())

        self.app.settings.setValue("LoadR", self.load_resistance.text())
        self.app.settings.setValue("LoadL", self.load_inductance.text())
        self.app.settings.setValue("LoadC", self.load_capacitance.text())
        self.app.settings.setValue("LoadDelay", self.load_length.text())

        self.app.settings.setValue("ThroughDelay", self.through_length.text())

        self.app.settings.endArray()
        self.app.settings.sync()
        self.listCalibrationStandards()
        self.cal_standard_save_selector.setCurrentText(name)

    def loadCalibrationStandard(self):
        if self.cal_standard_save_selector.currentData() == -1:
            return
        read_num = self.cal_standard_save_selector.currentData()
        logger.debug("Loading calibration no %d", read_num)
        self.app.settings.beginReadArray("CalibrationStandards")
        self.app.settings.setArrayIndex(read_num)

        name = self.app.settings.value("Name")
        logger.info("Loading: %s", name)

        self.short_l0_input.setText(str(self.app.settings.value("ShortL0", 0)))
        self.short_l1_input.setText(str(self.app.settings.value("ShortL1", 0)))
        self.short_l2_input.setText(str(self.app.settings.value("ShortL2", 0)))
        self.short_l3_input.setText(str(self.app.settings.value("ShortL3", 0)))
        self.short_length.setText(str(self.app.settings.value("ShortDelay", 0)))

        self.open_c0_input.setText(str(self.app.settings.value("OpenC0", 50)))
        self.open_c1_input.setText(str(self.app.settings.value("OpenC1", 0)))
        self.open_c2_input.setText(str(self.app.settings.value("OpenC2", 0)))
        self.open_c3_input.setText(str(self.app.settings.value("OpenC3", 0)))
        self.open_length.setText(str(self.app.settings.value("OpenDelay", 0)))

        self.load_resistance.setText(str(self.app.settings.value("LoadR", 50)))
        self.load_inductance.setText(str(self.app.settings.value("LoadL", 0)))
        self.load_capacitance.setText(str(self.app.settings.value("LoadC", 0)))
        self.load_length.setText(str(self.app.settings.value("LoadDelay", 0)))

        self.through_length.setText(
            str(self.app.settings.value("ThroughDelay", 0))
        )

        self.app.settings.endArray()

    def deleteCalibrationStandard(self):
        if self.cal_standard_save_selector.currentData() == -1:
            return
        delete_num = self.cal_standard_save_selector.currentData()
        logger.debug("Deleting calibration no %d", delete_num)
        num_standards = self.app.settings.beginReadArray("CalibrationStandards")
        self.app.settings.endArray()

        logger.debug("Number of standards known: %d", num_standards)

        if num_standards == 1:
            logger.debug("Only one standard known")
            self.app.settings.beginWriteArray("CalibrationStandards", 0)
            self.app.settings.endArray()
        else:
            names = []

            shortL0 = []
            shortL1 = []
            shortL2 = []
            shortL3 = []
            shortDelay = []

            openC0 = []
            openC1 = []
            openC2 = []
            openC3 = []
            openDelay = []

            loadR = []
            loadL = []
            loadC = []
            loadDelay = []

            throughDelay = []

            self.app.settings.beginReadArray("CalibrationStandards")
            for i in range(num_standards):
                if i == delete_num:
                    continue
                self.app.settings.setArrayIndex(i)
                names.append(self.app.settings.value("Name"))

                shortL0.append(self.app.settings.value("ShortL0"))
                shortL1.append(self.app.settings.value("ShortL1"))
                shortL2.append(self.app.settings.value("ShortL2"))
                shortL3.append(self.app.settings.value("ShortL3"))
                shortDelay.append(self.app.settings.value("ShortDelay"))

                openC0.append(self.app.settings.value("OpenC0"))
                openC1.append(self.app.settings.value("OpenC1"))
                openC2.append(self.app.settings.value("OpenC2"))
                openC3.append(self.app.settings.value("OpenC3"))
                openDelay.append(self.app.settings.value("OpenDelay"))

                loadR.append(self.app.settings.value("LoadR"))
                loadL.append(self.app.settings.value("LoadL"))
                loadC.append(self.app.settings.value("LoadC"))
                loadDelay.append(self.app.settings.value("LoadDelay"))

                throughDelay.append(self.app.settings.value("ThroughDelay"))
            self.app.settings.endArray()

            self.app.settings.beginWriteArray("CalibrationStandards")
            self.app.settings.remove("")
            self.app.settings.endArray()

            self.app.settings.beginWriteArray(
                "CalibrationStandards", len(names)
            )
            for i, name in enumerate(names):
                self.app.settings.setArrayIndex(i)
                self.app.settings.setValue("Name", name)

                self.app.settings.setValue("ShortL0", shortL0[i])
                self.app.settings.setValue("ShortL1", shortL1[i])
                self.app.settings.setValue("ShortL2", shortL2[i])
                self.app.settings.setValue("ShortL3", shortL3[i])
                self.app.settings.setValue("ShortDelay", shortDelay[i])

                self.app.settings.setValue("OpenC0", openC0[i])
                self.app.settings.setValue("OpenC1", openC1[i])
                self.app.settings.setValue("OpenC2", openC2[i])
                self.app.settings.setValue("OpenC3", openC3[i])
                self.app.settings.setValue("OpenDelay", openDelay[i])

                self.app.settings.setValue("LoadR", loadR[i])
                self.app.settings.setValue("LoadL", loadL[i])
                self.app.settings.setValue("LoadC", loadC[i])
                self.app.settings.setValue("LoadDelay", loadDelay[i])

                self.app.settings.setValue("ThroughDelay", throughDelay[i])
            self.app.settings.endArray()

        self.app.settings.sync()
        self.listCalibrationStandards()

    def reset(self):
        self.app.calibration = Calibration()
        for label in self.cal_label.values():
            label.setText("Uncalibrated")
        self.calibration_status_label.setText("Device calibration")
        self.calibration_source_label.setText("Device")
        self.notes_textedit.clear()
        self.short_touchstone = None
        self.open_touchstone = None
        self.load_touchstone = None

        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Saving and displaying raw data.")
            self.app.saveData(
                self.app.worker.rawData11,
                self.app.worker.rawData21,
                self.app.sweepSource,
            )
            self.app.worker.signals.updated.emit()
        self.app.sweep_control.update_text()

    def setOffsetDelay(self, value: float):
        logger.debug("New offset delay value: %f ps", value)
        self.app.worker.offsetDelay = value / 1e12
        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Applying new offset to existing sweep data.")
            (
                self.app.worker.data11,
                self.app.worker.data21,
            ) = self.app.worker.applyCalibration(
                self.app.worker.rawData11, self.app.worker.rawData21
            )
            logger.debug("Saving and displaying corrected data.")
            self.app.saveData(
                self.app.worker.data11,
                self.app.worker.data21,
                self.app.sweepSource,
            )
            self.app.worker.signals.updated.emit()

    def calculate(self):
        cal_element = self.app.calibration.cal_element
        if self.app.sweep_control.btn_stop.isEnabled():
            self.app.showError(
                "扫频正在运行中，无法应用校准。"
                " 请停止扫频后重试。"
            )
            return

        if not self.app.calibration.isValid1Port():
            self.app.showError(
                "校准数据不足，无法应用校准。"
                " 请完成 SOL 校准后再试。"
            )
            return

        cal_element.short_state = "IDEAL"
        cal_element.open_state = "IDEAL"
        cal_element.load_state = "IDEAL"
        cal_element.through_is_ideal = True

        # TODO: all ideal or not?
        if self.radio_group.checkedButton() == self.use_coefficients:
            cal_element.short_state = "COEFF"
            cal_element.open_state = "COEFF"
            cal_element.load_state = "COEFF"
            cal_element.through_is_ideal = False

            # We are using custom calibration standards

            cal_element.short_l0 = (
                getFloatValue(self.short_l0_input.text()) / 1.0e12
            )
            cal_element.short_l1 = (
                getFloatValue(self.short_l1_input.text()) / 1.0e24
            )
            cal_element.short_l2 = (
                getFloatValue(self.short_l2_input.text()) / 1.0e33
            )
            cal_element.short_l3 = (
                getFloatValue(self.short_l3_input.text()) / 1.0e42
            )
            cal_element.short_length = (
                getFloatValue(self.short_length.text()) / 1.0e12
            )

            cal_element.open_c0 = (
                getFloatValue(self.open_c0_input.text()) / 1.0e15
            )
            cal_element.open_c1 = (
                getFloatValue(self.open_c1_input.text()) / 1.0e27
            )
            cal_element.open_c2 = (
                getFloatValue(self.open_c2_input.text()) / 1.0e36
            )
            cal_element.open_c3 = (
                getFloatValue(self.open_c3_input.text()) / 1.0e45
            )
            cal_element.open_length = (
                getFloatValue(self.open_length.text()) / 1.0e12
            )

            cal_element.load_r = getFloatValue(self.load_resistance.text())
            cal_element.load_l = (
                getFloatValue(self.load_inductance.text()) / 1.0e12
            )
            cal_element.load_c = (
                getFloatValue(self.load_capacitance.text()) / 1.0e15
            )
            cal_element.load_length = (
                getFloatValue(self.load_length.text()) / 1.0e12
            )

            cal_element.through_length = (
                getFloatValue(self.through_length.text()) / 1.0e12
            )
        elif self.radio_group.checkedButton() == self.use_s1p_files:
            if self.short_touchstone is not None:
                cal_element.short_state = "FILE"
                cal_element.short_touchstone = self.short_touchstone
            if self.open_touchstone is not None:
                cal_element.open_state = "FILE"
                cal_element.open_touchstone = self.open_touchstone
            if self.load_touchstone is not None:
                cal_element.load_state = "FILE"
                cal_element.load_touchstone = self.load_touchstone
            cal_element.through_is_ideal = False
            cal_element.through_length = (
                getFloatValue(self.through_length.text()) / 1.0e12
            )

        logger.debug("Attempting calibration calculation.")
        try:
            self.app.calibration.calc_corrections()
            self.calibration_status_label.setText(
                _format_cal_label(
                    self.app.calibration.size(), "软件计算校准"
                )
            )
            if self.use_ideal_values.isChecked():
                self.calibration_source_label.setText(
                    self.app.calibration.source
                )
            else:
                self.calibration_source_label.setText(
                    f"{self.app.calibration.source} (校准件: 自定义)"
                )

            if self.app.worker.rawData11:
                # There's raw data, so we can get corrected data
                logger.debug("Applying calibration to existing sweep data.")
                (
                    self.app.worker.data11,
                    self.app.worker.data21,
                ) = self.app.worker.applyCalibration(
                    self.app.worker.rawData11, self.app.worker.rawData21
                )
                logger.debug("Saving and displaying corrected data.")
                self.app.saveData(
                    self.app.worker.data11,
                    self.app.worker.data21,
                    self.app.sweepSource,
                )
                self.app.worker.signals.updated.emit()

        except ValueError as e:
            # showError here hides the calibration window,
            # so we need to pop up our own
            self.calibration_status_label.setText(
                "应用校准失败。"
            )
            self.calibration_source_label.setText(self.app.calibration.source)
            self.app.showError(
                f"{e} 请完成 SOL 校准后再试。"
            )
            self.reset()
            return
        self.app.sweep_control.update_text()

    def loadCalibration(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="校准文件 (*.cal);;所有文件 (*.*)"
        )
        if filename:
            self.app.calibration.load(filename)
        if not self.app.calibration.isValid1Port():
            return
        for i, name in enumerate(
            ("short", "open", "load", "through", "isolation", "thrurefl")
        ):
            self.cal_label[name].setText(
                _format_cal_label(
                    self.app.calibration.data_size(name), "已加载"
                )
            )
            if i == 2 and not self.app.calibration.isValid2Port():
                break
        self.calculate()
        self.notes_textedit.clear()
        for note in self.app.calibration.notes:
            self.notes_textedit.appendPlainText(note)
        self.app.settings.setValue("CalibrationFile", filename)
        self.app.sweep_control.update_text()

    def saveCalibration(self):
        if not self.app.calibration.isCalculated:
            logger.debug("Attempted to save an uncalculated calibration.")
            self.app.showError("无法保存未应用的校准状态。")
            return
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("cal")
        filedialog.setNameFilter("校准文件 (*.cal);;所有文件 (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        if filedialog.exec():
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if not filename:
            logger.debug("No file name selected.")
            return
        self.app.calibration.notes = (
            self.notes_textedit.toPlainText().splitlines()
        )
        try:
            self.app.calibration.save(filename)
            self.app.settings.setValue("CalibrationFile", filename)
        except IOError:
            logger.error("Calibration save failed!")
            self.app.showError("保存校准文件失败。")

    def calStandardChanged(self, button):
        if button == self.use_ideal_values:
            self.cal_short_box.setDisabled(True)
            self.cal_open_box.setDisabled(True)
            self.cal_load_box.setDisabled(True)
            self.cal_through_box.setDisabled(True)
            self.cal_standard_save_box.setDisabled(True)
            self.file_button_short.setDisabled(True)
            self.file_button_open.setDisabled(True)
            self.file_button_load.setDisabled(True)
        elif button == self.use_s1p_files:
            self.cal_short_box.setDisabled(True)
            self.cal_open_box.setDisabled(True)
            self.cal_load_box.setDisabled(True)
            self.cal_through_box.setDisabled(False)
            self.cal_standard_save_box.setDisabled(True)
            self.file_button_short.setDisabled(False)
            self.file_button_open.setDisabled(False)
            self.file_button_load.setDisabled(False)
        elif button == self.use_coefficients:
            self.cal_short_box.setDisabled(False)
            self.cal_open_box.setDisabled(False)
            self.cal_load_box.setDisabled(False)
            self.cal_through_box.setDisabled(False)
            self.cal_standard_save_box.setDisabled(False)
            self.file_button_short.setDisabled(True)
            self.file_button_open.setDisabled(True)
            self.file_button_load.setDisabled(True)

    def automaticCalibration(self):
        self.btn_automatic.setDisabled(True)
        introduction = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Information,
            "校准向导",
            (
                "本校准向导将协助您在 NanoVNASaver 中完成校准。向导将依次扫频采集各校准件数据并引导您完成全流程。<br><br>"
                "在开始前，请确保准备好开路 (Open)、短路 (Short) 和负载 (Load)"
                " 校准件，并将待校准的测试电缆连接至仪器端口。<br><br>"
                '若需执行双端口 (2-Port) 校准，还需准备“直通 (Thru)”'
                " 连接件。<br><br>"
                "<b>提示：在开始前，建议先在 NanoVNA 设备端完成全频段硬件校准并保存至 0 号槽位，以获得最佳测量精度。</b><br><br>"
                "准备就绪后，请点击“确定”继续。"
            ),
            QtWidgets.QMessageBox.StandardButton.Ok
            | QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        response = introduction.exec()
        if response != QtWidgets.QMessageBox.StandardButton.Ok:
            self.btn_automatic.setDisabled(False)
            return
        logger.info("Starting automatic calibration assistant.")
        if not self.app.vna.connected():
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "NanoVNA 未连接",
                (
                    "在校准前请先确认已成功连接 NanoVNA 设备。"
                ),
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        if self.app.sweep.properties.mode == SweepMode.CONTINOUS:
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "连续扫频已开启",
                (
                    "在执行校准前，请先关闭连续扫频。"
                ),
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        short_step = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Information,
            "短路校准 (Short)",
            (
                '请将“短路 (Short)”校准件连接至 NanoVNA 的端口 0 (CH0)。\n\n'
                "准备就绪后点击“确定”继续。"
            ),
            QtWidgets.QMessageBox.StandardButton.Ok
            | QtWidgets.QMessageBox.StandardButton.Cancel,
        )

        response = short_step.exec()
        if response != QtWidgets.QMessageBox.StandardButton.Ok:
            self.btn_automatic.setDisabled(False)
            return
        self.reset()
        self.app.calibration.source = "校准向导"
        self.next_step = 0
        self.app.worker.signals.finished.connect(self.automaticCalibrationStep)
        self.app.sweep_start()
        return

    def automaticCalibrationStep(self):
        if self.next_step == -1:
            self.app.worker.signals.finished.disconnect(
                self.automaticCalibrationStep
            )
            return

        if self.next_step == 0:
            # Short
            self.cal_save("short")
            self.next_step = 1

            open_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "开路校准 (Open)",
                (
                    '请将“开路 (Open)”校准件连接至 NanoVNA 的端口 0 (CH0)。\n\n'
                    "可使用配套的标准开路件，或者保持电缆末端悬空开路。\n\n"
                    "准备就绪后点击“确定”继续。"
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = open_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.next_step = -1
                self.btn_automatic.setDisabled(False)
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self.app.sweep_start()
            return

        if self.next_step == 1:
            # Open
            self.cal_save("open")
            self.next_step = 2
            load_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "负载校准 (Load)",
                (
                    '请将“负载 (Load)”校准件连接至 NanoVNA 的端口 0 (CH0)。\n\n'
                    "准备就绪后点击“确定”继续。"
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = load_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self.app.sweep_start()
            return

        if self.next_step == 2:
            # Load
            self.cal_save("load")
            self.next_step = 3
            continue_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "单端口 (1-Port) 校准完成",
                (
                    "单端口校准所需的步骤已全部完成。\n\n"
                    "若需继续执行双端口 (2-Port) 校准，请点击“Yes”；"
                    '若仅应用单端口校准并结束向导，请点击“Apply”。'
                ),
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.Apply
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = continue_step.exec()
            if response == QtWidgets.QMessageBox.StandardButton.Apply:
                self.calculate()
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                self.btn_automatic.setDisabled(False)
                return
            if response != QtWidgets.QMessageBox.StandardButton.Yes:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return

            isolation_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "隔离度校准 (Isolation)",
                (
                    '请将“负载 (Load)”校准件连接至 NanoVNA 的端口 1 (CH1)。\n\n'
                    "若有第二个负载校准件，亦可同时接在端口 0 (CH0)。\n\n"
                    "准备就绪后点击“确定”继续。"
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = isolation_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self.app.sweep_start()
            return

        if self.next_step == 3:
            # Isolation
            self.cal_save("isolation")
            self.next_step = 4
            through_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "直通校准 (Thru)",
                (
                    '请在 NanoVNA 端口 0 (CH0) 与端口 1 (CH1) 之间连接“直通 (Thru)”标准件。\n\n'
                    "准备就绪后点击“确定”继续。"
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = through_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self.app.sweep_start()
            return

        if self.next_step == 4:
            # Done
            self.cal_save("thrurefl")
            self.cal_save("through")
            apply_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "校准完成",
                (
                    "校准测量流程已完成。点击“Apply”以计算并应用校准参数。"
                ),
                QtWidgets.QMessageBox.StandardButton.Apply
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = apply_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Apply:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return

            self.calculate()
            self.btn_automatic.setDisabled(False)
            self.next_step = -1
            self.app.worker.signals.finished.disconnect(
                self.automaticCalibrationStep
            )
            return

    def select_file_open(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择开路 (Open) S1P 文件", "", "Touchstone 文件 (*.s1p)"
        )
        if filename != "":
            self.open_touchstone = Touchstone(filename)
            self.open_touchstone.load()

    def select_file_short(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择短路 (Short) S1P 文件", "", "Touchstone 文件 (*.s1p)"
        )
        if filename != "":
            self.short_touchstone = Touchstone(filename)
            self.short_touchstone.load()

    def select_file_load(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择负载 (Load) S1P 文件", "", "Touchstone 文件 (*.s1p)"
        )
        if filename != "":
            self.load_touchstone = Touchstone(filename)
            self.load_touchstone.load()
