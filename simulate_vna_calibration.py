#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
矢量网络分析仪（VNA）SOLT 单端口误差校准模型与计算示例
功能：
  1. 待测件天线模型
  2. 传输线与系统误差模型 (ED, ES, ERF)
  3. 短路 (Short)、开路 (Open)、负载 (Load) 测量值计算
  4. SOLT 误差矩阵求解与反校正验证
=============================================================================
"""

import math
import sys
import numpy as np

# 确保在 Windows 控制台输出正确的 UTF-8 中文
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 尝试导入 matplotlib 用于绘图
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def z_to_gamma(z: complex, z0: float = 50.0) -> complex:
    """将复阻抗 Z 转换为电压反射系数 Gamma"""
    return (z - z0) / (z + z0)


def gamma_to_vswr(gamma: complex) -> float:
    """由反射系数计算电压驻波比 (VSWR)"""
    mag = abs(gamma)
    if mag >= 0.9999:
        return 999.0
    return (1.0 + mag) / (1.0 - mag)


def gamma_to_return_loss_db(gamma: complex) -> float:
    """由反射系数计算回波损耗 (Return Loss, dB)"""
    mag = abs(gamma)
    if mag <= 1e-6:
        return 120.0
    return -20.0 * math.log10(mag)


# ----------------------------------------------------------------------
# 1. 生成频段与真实待测件（DUT）天线阻抗模型
# ----------------------------------------------------------------------
freqs = np.linspace(400e6, 600e6, 101)  # 400 MHz ~ 600 MHz, 101 个频点
f0 = 500e6  # 天线中心谐振频率 500 MHz
R0 = 50.0   # 传输线基准特征阻抗 50 欧姆

# 模型：一个在 500 MHz 谐振的 RLC 串联谐振回路天线
# 阻抗 Z(f) = R + j * (2*pi*f*L - 1/(2*pi*f*C))
R_antenna = 51.5  # 谐振点纯阻略微偏移 50 欧姆
Q_antenna = 12.0  # 品质因数
L_ant = (Q_antenna * R_antenna) / (2 * np.pi * f0)
C_ant = 1.0 / ((2 * np.pi * f0) ** 2 * L_ant)

# 计算天线真实的真实物理反射系数 Gamma_actual
gamma_dut_actual = []
for f in freqs:
    omega = 2 * np.pi * f
    X = omega * L_ant - 1.0 / (omega * C_ant)
    Z = complex(R_antenna, X)
    gamma_dut_actual.append(z_to_gamma(Z, R0))
gamma_dut_actual = np.array(gamma_dut_actual)

# ----------------------------------------------------------------------
# 2. 建立射频仪器与测试同轴电缆的 3 项系统误差模型 (1-Port Error Model)
# ----------------------------------------------------------------------
# ED (Directivity 方向性误差): 内部定向耦合器泄漏，典型值约 -28 dB
# ES (Source Match 源匹配误差): 信号源内阻非理想 50 欧姆，典型值约 -22 dB
# ERF (Reflection Tracking 反射跟踪误差): 线缆双程衰减与电长度相位延迟
cable_length = 0.6  # 60 cm 长的测试线缆
vp = 0.67 * 3e8     # 聚四氟乙烯介质电缆中的光速 (速度因子 0.67)
cable_delay = (2 * cable_length) / vp  # 双程时延约 6.0 ns
cable_attenuation_per_m_ghz = 0.8      # 线缆衰减 (dB/m @ 1GHz)

ED = np.zeros(len(freqs), dtype=complex)
ES = np.zeros(len(freqs), dtype=complex)
ERF = np.zeros(len(freqs), dtype=complex)

for i, f in enumerate(freqs):
    # 方向性误差随着频点有随机相位漂移
    phase_ed = 2 * np.pi * (f / 1e8) * 0.4
    ed_mag = 0.040  # 约 -28 dB
    ED[i] = complex(ed_mag * np.cos(phase_ed), ed_mag * np.sin(phase_ed))

    # 源匹配误差
    phase_es = 2 * np.pi * (f / 1e8) * 0.7
    es_mag = 0.075  # 约 -22.5 dB
    ES[i] = complex(es_mag * np.cos(phase_es), es_mag * np.sin(phase_es))

    # 反射跟踪误差：包含双程插损与巨大的相位旋转 (2*pi*f*delay)
    att_db = cable_attenuation_per_m_ghz * (2 * cable_length) * math.sqrt(f / 1e9)
    erf_mag = 10.0 ** (-att_db / 20.0)
    phase_erf = -2 * np.pi * f * cable_delay
    ERF[i] = complex(erf_mag * np.cos(phase_erf), erf_mag * np.sin(phase_erf))


def vna_measure(gamma_true, ed, es, erf):
    """
    根据矢网信号流图计算实际测量值 (带系统误差的脏数据)：
    Gamma_M = ED + (ERF * Gamma_A) / (1 - ES * Gamma_A)
    """
    return ed + (erf * gamma_true) / (1.0 - es * gamma_true)


# ----------------------------------------------------------------------
# 3. 模拟测量过程：采集校准标准件 (Short, Open, Load) 与待测天线
# ----------------------------------------------------------------------
# 理想校准件物理反射系数：
GAMMA_SHORT_TRUE = -1.0 + 0.0j  # 短路：Gamma = -1
GAMMA_OPEN_TRUE = 1.0 + 0.0j   # 开路：Gamma = +1
GAMMA_LOAD_TRUE = 0.0 + 0.0j   # 负载：Gamma = 0 (匹配 50 欧)

# 模拟仪器实际测出的测量值 (包含线缆及内部误差)
gamma_meas_short = vna_measure(GAMMA_SHORT_TRUE, ED, ES, ERF)
gamma_meas_open = vna_measure(GAMMA_OPEN_TRUE, ED, ES, ERF)
gamma_meas_load = vna_measure(GAMMA_LOAD_TRUE, ED, ES, ERF)

# 模拟测量待测天线 (未经校准的原始数据)
gamma_meas_dut_raw = vna_measure(gamma_dut_actual, ED, ES, ERF)

# ----------------------------------------------------------------------
# 4. SOLT 算法求解 3 项系统误差 (反解方程组)
# ----------------------------------------------------------------------
# 依据公式：
# 1) E_D = Gamma_meas_load
# 2) E_S = [2*E_D - (Gamma_MS + Gamma_MO)] / (Gamma_MS - Gamma_MO)
# 3) Delta_E = 0.5 * [(Gamma_MS - Gamma_MO) + E_S*(Gamma_MS + Gamma_MO)]
# 4) E_RF = E_D * E_S - Delta_E
solved_ED = np.zeros(len(freqs), dtype=complex)
solved_ES = np.zeros(len(freqs), dtype=complex)
solved_ERF = np.zeros(len(freqs), dtype=complex)

for i in range(len(freqs)):
    ms = gamma_meas_short[i]
    mo = gamma_meas_open[i]
    ml = gamma_meas_load[i]

    ed_cal = ml
    es_cal = (2.0 * ed_cal - (ms + mo)) / (ms - mo)
    delta_e = 0.5 * ((ms - mo) + es_cal * (ms + mo))
    erf_cal = ed_cal * es_cal - delta_e

    solved_ED[i] = ed_cal
    solved_ES[i] = es_cal
    solved_ERF[i] = erf_cal

# ----------------------------------------------------------------------
# 5. 误差修正（De-embedding 校准反演）
# ----------------------------------------------------------------------
# 校准修正公式：
# Gamma_calibrated = (Gamma_meas - E_D) / [E_RF + E_S * (Gamma_meas - E_D)]
gamma_dut_calibrated = np.zeros(len(freqs), dtype=complex)
for i in range(len(freqs)):
    gm = gamma_meas_dut_raw[i]
    ed = solved_ED[i]
    es = solved_ES[i]
    erf = solved_ERF[i]

    diff = gm - ed
    gamma_dut_calibrated[i] = diff / (erf + es * diff)

# ----------------------------------------------------------------------
# 6. 输出对比分析与打印报表
# ----------------------------------------------------------------------
print("=" * 80)
print("     矢量网络分析仪 (NanoVNA) SOLT 系统误差校准数学模型与仿真验证     ")
print("=" * 80)
print(f"频段范围: {freqs[0]/1e6:.1f} MHz ~ {freqs[-1]/1e6:.1f} MHz, 共 {len(freqs)} 点")
print(f"待测件(DUT): 500 MHz 中心谐振单极子天线 (50Ω 微波端口)")
print(f"模拟测试环境: 引入 60cm 传输线缆相位延迟 (~6ns) 与 耦合器漏波误差")
print("-" * 80)

# 选取 3 个特征频点打印对比：带外 450MHz、谐振中心 500MHz、带外 550MHz
test_indices = [25, 50, 75]  # 对应约 450MHz, 500MHz, 550MHz

print(f"{'频点 (MHz)':<12} | {'对比状态':<14} | {'复数反射系数 Gamma':<28} | {'回波损耗 (dB)':<14} | {'驻波比 (VSWR)':<10}")
print("-" * 80)

for idx in test_indices:
    f_mhz = freqs[idx] / 1e6
    g_act = gamma_dut_actual[idx]
    g_raw = gamma_meas_dut_raw[idx]
    g_cal = gamma_dut_calibrated[idx]

    print(f"{f_mhz:<12.1f} | {'1.真实物理值':<12} | {f'{g_act.real:+.4f}{g_act.imag:+.4f}j':<28} | {gamma_to_return_loss_db(g_act):<14.2f} | {gamma_to_vswr(g_act):<10.2f}")
    print(f"{'':<12} | {'2.未校准测量(脏)':<10} | {f'{g_raw.real:+.4f}{g_raw.imag:+.4f}j':<28} | {gamma_to_return_loss_db(g_raw):<14.2f} | {gamma_to_vswr(g_raw):<10.2f}")
    print(f"{'':<12} | {'3.SOLT校准后':<12} | {f'{g_cal.real:+.4f}{g_cal.imag:+.4f}j':<28} | {gamma_to_return_loss_db(g_cal):<14.2f} | {gamma_to_vswr(g_cal):<10.2f}")
    print("-" * 80)

# 计算全频段最大校准残余误差
residual_error = np.max(np.abs(gamma_dut_calibrated - gamma_dut_actual))
print(f"\n[验证结论] 全频段校准恢复最大残余误差: {residual_error:.2e} (完全数值精确收敛！)")
print("说明: 未校准时，由于 60cm 线缆引入的相位旋转，阻抗轨迹在史密斯圆图上高速打转；")
print("      经过 SOLT 校准后，系统误差与线缆延时被数学完全消除，曲线精准恢复到 50Ω 参考面！\n")

def generate_svg_chart(filename="vna_solt_simulation_result.svg"):
    """零第三方依赖生成高清矢量 SVG 对比图表"""
    rl_act = [gamma_to_return_loss_db(g) for g in gamma_dut_actual]
    rl_raw = [gamma_to_return_loss_db(g) for g in gamma_meas_dut_raw]
    rl_cal = [gamma_to_return_loss_db(g) for g in gamma_dut_calibrated]

    w, h = 900, 480
    f_min, f_max = freqs[0] / 1e6, freqs[-1] / 1e6
    rl_min, rl_max = 0, 40

    def f_to_x(f_val):
        return 80 + (f_val - f_min) / (f_max - f_min) * 360

    def rl_to_y(rl_val):
        clamped = max(0, min(40, rl_val))
        return 400 - (clamped - rl_min) / (rl_max - rl_min) * 320

    # 生成折线 path
    path_act = "M " + " ".join([f"{f_to_x(f/1e6):.1f},{rl_to_y(r):.1f}" for f, r in zip(freqs, rl_act)])
    path_raw = "M " + " ".join([f"{f_to_x(f/1e6):.1f},{rl_to_y(r):.1f}" for f, r in zip(freqs, rl_raw)])
    path_cal = "M " + " ".join([f"{f_to_x(f/1e6):.1f},{rl_to_y(r):.1f}" for f, r in zip(freqs, rl_cal)])

    # 极坐标圆图坐标转换
    cx, cy, r_radius = 680, 240, 150
    def g_to_polar(g):
        gx = cx + g.real * r_radius
        gy = cy - g.imag * r_radius
        return f"{gx:.1f},{gy:.1f}"

    polar_act = "M " + " ".join([g_to_polar(g) for g in gamma_dut_actual])
    polar_raw = "M " + " ".join([g_to_polar(g) for g in gamma_meas_dut_raw])
    polar_cal = "M " + " ".join([g_to_polar(g) for g in gamma_dut_calibrated])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="background-color: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', sans-serif;">
      <!-- 标题 -->
      <text x="450" y="35" fill="#f0f0f0" font-size="20" font-weight="bold" text-anchor="middle">NanoVNA SOLT 系统误差校准数学模型仿真结果</text>

      <!-- 左图: S11 回波损耗对比 -->
      <text x="260" y="65" fill="#e0e0e0" font-size="15" font-weight="bold" text-anchor="middle">S11 回波损耗对比 (Return Loss)</text>
      <!-- 网格与坐标轴 -->
      <rect x="80" y="80" width="360" height="320" fill="#252526" stroke="#444" />
      <line x1="80" y1="160" x2="440" y2="160" stroke="#333" stroke-dasharray="4,4" />
      <line x1="80" y1="240" x2="440" y2="240" stroke="#333" stroke-dasharray="4,4" />
      <line x1="80" y1="320" x2="440" y2="320" stroke="#333" stroke-dasharray="4,4" />
      <line x1="170" y1="80" x2="170" y2="400" stroke="#333" stroke-dasharray="4,4" />
      <line x1="260" y1="80" x2="260" y2="400" stroke="#333" stroke-dasharray="4,4" />
      <line x1="350" y1="80" x2="350" y2="400" stroke="#333" stroke-dasharray="4,4" />

      <!-- 刻度标签 -->
      <text x="70" y="405" fill="#aaa" font-size="11" text-anchor="end">0 dB</text>
      <text x="70" y="325" fill="#aaa" font-size="11" text-anchor="end">10 dB</text>
      <text x="70" y="245" fill="#aaa" font-size="11" text-anchor="end">20 dB</text>
      <text x="70" y="165" fill="#aaa" font-size="11" text-anchor="end">30 dB</text>
      <text x="70" y="85" fill="#aaa" font-size="11" text-anchor="end">40 dB</text>

      <text x="80" y="425" fill="#aaa" font-size="11" text-anchor="middle">400 MHz</text>
      <text x="170" y="425" fill="#aaa" font-size="11" text-anchor="middle">450 MHz</text>
      <text x="260" y="425" fill="#aaa" font-size="11" text-anchor="middle">500 MHz (谐振)</text>
      <text x="350" y="425" fill="#aaa" font-size="11" text-anchor="middle">550 MHz</text>
      <text x="440" y="425" fill="#aaa" font-size="11" text-anchor="middle">600 MHz</text>

      <!-- 左图曲线 -->
      <path d="{path_raw}" fill="none" stroke="#ff5555" stroke-width="2" stroke-dasharray="4,4" />
      <path d="{path_act}" fill="none" stroke="#55ff55" stroke-width="3" opacity="0.6" />
      <path d="{path_cal}" fill="none" stroke="#33aaff" stroke-width="2" />

      <!-- 右图: 极坐标/复平面反射系数 -->
      <text x="680" y="65" fill="#e0e0e0" font-size="15" font-weight="bold" text-anchor="middle">反射系数复平面轨迹 (极坐标/Smith图基底)</text>
      <circle cx="{cx}" cy="{cy}" r="{r_radius}" fill="#252526" stroke="#555" />
      <circle cx="{cx}" cy="{cy}" r="{r_radius*0.66}" fill="none" stroke="#333" stroke-dasharray="3,3" />
      <circle cx="{cx}" cy="{cy}" r="{r_radius*0.33}" fill="none" stroke="#333" stroke-dasharray="3,3" />
      <line x1="{cx - r_radius}" y1="{cy}" x2="{cx + r_radius}" y2="{cy}" stroke="#444" />
      <line x1="{cx}" y1="{cy - r_radius}" x2="{cx}" y2="{cy + r_radius}" stroke="#444" />
      <text x="{cx + r_radius + 5}" y="{cy + 4}" fill="#888" font-size="10">+1(开路)</text>
      <text x="{cx - r_radius - 5}" y="{cy + 4}" fill="#888" font-size="10" text-anchor="end">-1(短路)</text>
      <text x="{cx}" y="{cy - r_radius - 5}" fill="#888" font-size="10" text-anchor="middle">+j</text>
      <text x="{cx}" y="{cy + r_radius + 15}" fill="#888" font-size="10" text-anchor="middle">-j</text>
      <circle cx="{cx}" cy="{cy}" r="3" fill="#ffaa00" />
      <text x="{cx + 6}" y="{cy - 6}" fill="#ffaa00" font-size="10">50Ω 理想负载匹配点</text>

      <!-- 右图曲线 -->
      <path d="{polar_raw}" fill="none" stroke="#ff5555" stroke-width="2" stroke-dasharray="3,3" />
      <path d="{polar_act}" fill="none" stroke="#55ff55" stroke-width="3" opacity="0.6" />
      <path d="{polar_cal}" fill="none" stroke="#33aaff" stroke-width="2" />

      <!-- 图例 Legend -->
      <rect x="180" y="445" width="540" height="26" rx="4" fill="#2d2d30" stroke="#444" />
      <line x1="200" y1="458" x2="230" y2="458" stroke="#ff5555" stroke-width="2" stroke-dasharray="4,4" />
      <text x="238" y="462" fill="#ff7777" font-size="12">未校准原始测量 (含线缆时延与泄漏)</text>

      <line x1="430" y1="458" x2="460" y2="458" stroke="#55ff55" stroke-width="3" />
      <text x="468" y="462" fill="#77ff77" font-size="12">真实天线物理值</text>

      <line x1="570" y1="458" x2="600" y2="458" stroke="#33aaff" stroke-width="2" />
      <text x="608" y="462" fill="#55ccff" font-size="12">SOLT 校准恢复值 (精准吻合)</text>
    </svg>
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"[高清矢量图生成成功] 结果已保存为: {filename} (可在浏览器直接查看)")

# 生成矢量图表
generate_svg_chart("vna_solt_simulation_result.svg")
print("=" * 80)

