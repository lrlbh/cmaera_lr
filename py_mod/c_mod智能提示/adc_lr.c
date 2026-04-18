"""
ADC Calibration Module for ESP32 (MicroPython Custom Module)
"""

def get_adc_cali() -> int:
    """
    检查并返回当前硬件支持的 ADC 校准方案掩码。
    
    返回值 (int):
        - 0: 未找到校准方案
        - 1: 支持 Line Fitting (线性拟合)
        - 2: 支持 Curve Fitting (曲线拟合)
        - 4: 硬件集成了 Vref
    """
    ...