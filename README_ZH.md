# NanoVNA-Saver 简体中文汉化版

本项目是开源射频矢量网络分析仪上位机 [NanoVNA-Saver](https://github.com/NanoVNA-Saver/nanovna-saver) 的简体中文汉化版本。

提供直接运行的 Windows 单文件可执行程序，方便国内用户与射频爱好者日常测试与使用。

---

## 主要调整与改进

1. **界面全量汉化**：
   * 对主控面板、标记读取、扫频设置、校准向导、TDR 及各分析窗口进行完整中文化；
   * 遵循射频领域常用规范（如短路 Short、开路 Open、负载 Load、直通 Thru 等），同时保留国际通用的符号与缩写（`S11`, `S21`, `VSWR`, `Return Loss`, `Smith Chart` 等）。

2. **排版与显示优化**：
   * 调整了频点标记（Marker）卡片的排版布局与宽度，避免在中文字符下数值与标签重叠；
   * 优化了串口设备下拉框的显示。

3. **稳定性与防卡死优化**：
   * 优化了连续扫频（Continuous Sweep）模式下的线程调度，避免扫频循环过度占用 CPU 导致主界面未响应或“停止”按钮无反应。

4. **内置虚拟演示设备**：
   * 内置虚拟演示设备驱动（Virtual NanoVNA），在电脑未连接物理硬件时也可直接启动软件体验扫频、图表交互及校准向导流程。

---

## 使用方法

### 方式 1：直接运行（推荐）
在 GitHub Releases 页面下载 `NanoVNASaver-ZH.exe`，双击即可直接打开使用，无需配置 Python 环境。

### 方式 2：从源码运行
1. 克隆代码：
   ```bash
   git clone https://github.com/qworkhard/NanoVNA-Saver-Chinese.git
   cd NanoVNA-Saver-Chinese
   ```
2. 创建并激活虚拟环境：
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. 安装依赖并启动：
   ```powershell
   pip install -e .
   python run.py
   ```

---

## 重新打包

如果对源码进行了修改，可在虚拟环境中使用 PyInstaller 打包：
```powershell
pip install pyinstaller
pyinstaller NanoVNASaver-ZH.spec
```
生成的可执行文件位于 `dist/NanoVNASaver-ZH.exe`。

---

## 协议与致谢

* 本项目基于 [NanoVNA-Saver](https://github.com/NanoVNA-Saver/nanovna-saver) 二次开发，遵循 **GPL-3.0** 开源协议。
* 原作者版权：
  * Copyright (C) 2019, 2020 Rune B. Broberg
  * Copyright (C) 2020-2024 NanoVNA-Saver Authors
