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
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

# from .ui import get_window_icon

logger = logging.getLogger(__name__)


class ScreenshotWindow(QtWidgets.QLabel):
    pix: Optional[QtGui.QPixmap] = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("设备屏幕截图")
        # TODO : self.setWindowIcon(get_window_icon())

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)
        self.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.ActionsContextMenu
        )

        self.action_original_size = QtGui.QAction("原始尺寸")
        self.action_original_size.triggered.connect(lambda: self.setScale(1))
        self.action_2x_size = QtGui.QAction("2倍放大")
        self.action_2x_size.triggered.connect(lambda: self.setScale(2))
        self.action_3x_size = QtGui.QAction("3倍放大")
        self.action_3x_size.triggered.connect(lambda: self.setScale(3))
        self.action_4x_size = QtGui.QAction("4倍放大")
        self.action_4x_size.triggered.connect(lambda: self.setScale(4))
        self.action_5x_size = QtGui.QAction("5倍放大")
        self.action_5x_size.triggered.connect(lambda: self.setScale(5))

        self.addAction(self.action_original_size)
        self.addAction(self.action_2x_size)
        self.addAction(self.action_3x_size)
        self.addAction(self.action_4x_size)
        self.addAction(self.action_5x_size)
        self.action_save_screenshot = QtGui.QAction("保存图片")
        self.action_save_screenshot.triggered.connect(self.saveScreenshot)
        self.addAction(self.action_save_screenshot)

    def setScreenshot(self, pixmap: QtGui.QPixmap):
        if ScreenshotWindow.pix is None:
            self.resize(pixmap.size())
        ScreenshotWindow.pix = pixmap
        self.setPixmap(
            ScreenshotWindow.pix.scaled(
                self.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.FastTransformation,
            )
        )
        w, h = pixmap.width(), pixmap.height()
        self.action_original_size.setText(
            f"原始尺寸 ({w}x{h})"
        )
        self.action_2x_size.setText(
            f"2倍放大 ({w * 2}x{h * 2})"
        )
        self.action_3x_size.setText(
            f"3倍放大 ({w * 3}x{h * 3})"
        )
        self.action_4x_size.setText(
            f"4倍放大 ({w * 4}x{h * 4})"
        )
        self.action_5x_size.setText(
            f"5倍放大 ({w * 5}x{h * 5})"
        )

    def saveScreenshot(self):
        if self.pix is not None:
            logger.info("Saving screenshot to file...")
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=self,
                caption="保存图片",
                filter="PNG 图像 (*.png);;所有文件 (*.*)",
            )

            logger.debug("Filename: %s", filename)
            if filename != "":
                self.pixmap().save(filename)
        else:
            logger.warning("The user got shown an empty screenshot window?")

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        if ScreenshotWindow.pix is not None:
            self.setPixmap(
                ScreenshotWindow.pix.scaled(
                    self.size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.FastTransformation,
                )
            )

    def setScale(self, scale):
        width, height = (
            self.pix.size().width() * scale,
            self.pix.size().height() * scale,
        )
        self.resize(width, height)
