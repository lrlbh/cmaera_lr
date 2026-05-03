# adc_cali_lr.pyi
# MicroPython stub file for adc_cali_lr C extension module
# ESP32-S3 ADC Calibration

def get_adc_cali() -> int:
    """查询当前芯片支持的 ADC 校准方案。

    Returns:
        int: 校准方案掩码 (adc_cali_scheme_ver_t)。
             常见值:
               ADC_CALI_SCHEME_VER_CURVE_FITTING = 1
               ADC_CALI_SCHEME_VER_LINE_FITTING  = 2

    Raises:
        Exception: 查询失败时抛出，附带错误码。
    """
    ...

def new_adc_cali(unit: int, atten: int, bitwidth: int, chan: int) -> int:
    """创建 ADC 校准对象，返回其句柄（以整数形式传递）。

    根据编译时宏自动选择 Curve Fitting 或 Line Fitting 方案。

    Args:
        unit:     ADC 单元 ID（ADC_UNIT_1 = 0, ADC_UNIT_2 = 1）。
        atten:    衰减系数（ADC_ATTEN_DB_0 / 2_5 / 6 / 11 / 12）。
        bitwidth: ADC 采样位宽（ADC_BITWIDTH_DEFAULT = 12, 9~12）。
        chan:     ADC 通道编号（ESP32-S3 上通常为 GPIO 编号 - 1）。

    Returns:
        int: 校准对象的句柄，传递给 adc_cali_data / adc_cali_close。

    Raises:
        Exception: 内存分配失败或校准方案创建失败时抛出。
    """
    ...

def adc_cali_data(adc_cali_in: int, in_data: int) -> int:
    """将 ADC 原始采样值转换为校准后的电压值（单位：mV）。

    Args:
        adc_cali_in: 由 new_adc_cali 返回的校准句柄。
        in_data:     ADC 原始采样值（0 ~ 2^bitwidth - 1）。

    Returns:
        int: 校准后的电压值，单位毫伏 (mV)。

    Raises:
        Exception: 转换失败时抛出，附带错误码。
    """
    ...

def adc_cali_close(adc_cali_in: int) -> None:
    """释放校准对象及其占用的资源。

    调用后句柄失效，不可再传递给 adc_cali_data。
    重复调用安全（handle 置 NULL 后不会重复释放）。

    Args:
        adc_cali_in: 由 new_adc_cali 返回的校准句柄。

    Returns:
        None

    Raises:
        Exception: 底层删除校准方案失败时抛出。
    """
    ...
