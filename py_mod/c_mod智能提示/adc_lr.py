# adc_lr.pyi
# MicroPython C module: adc_lr
# ESP32-S3 ADC Continuous Mode

from typing import List

# ADC 连续采集对象句柄（内部为指针，以 int 存储）
ADC_Handle = int


def new_adc(
    gpio: List[int],
    mem_buf_size: int,
    frame_buf_size: int,
    flush_flag: int,
    atten: List[int],
    unit: List[int],
    bit_width: List[int],
    sample_freq: int,
    format: int,
    conv_mode: int,
) -> ADC_Handle:
    """
    创建 ADC 连续采集对象并配置参数。

    Args:
        gpio:          ADC 通道列表，值 +1 后对应 S3 引脚号
        mem_buf_size:  内部缓冲区大小（字节），应 >= 帧大小的 2 倍
        frame_buf_size: 帧大小（字节），每个 ADC 值占 4 字节
        flush_flag:    缓冲区满时的行为
                         0 = 覆盖旧数据
                         1 = 清空缓冲区后重新存储
        atten:         每个通道的衰减列表
                         0 = 0dB, 1 = 2.5dB, 2 = 6dB, 3 = 12dB
        unit:          每个通道的 ADC 单元列表
                         0 = ADC1, 1 = ADC2（与 WiFi 冲突）
        bit_width:     每个通道的精度列表
                         9~13 = 指定位宽, 0 = 自动选择最大精度
        sample_freq:   采样频率（Hz），范围 611 ~ 83333
        format:        输出数据格式
                         S3 仅支持 1（TYPE2, 4字节）
        conv_mode:     ADC 转换模式
                         1 = 仅 ADC1
                         2 = 仅 ADC2
                         3 = 同时使用 ADC1 和 ADC2
                         7 = 交替使用 ADC1 和 ADC2

    Returns:
        ADC_Handle: ADC 对象句柄

    Raises:
        Exception: 创建或配置失败时抛出异常
    """
    ...


def adc_start(adc: ADC_Handle) -> None:
    """
    开启 ADC 连续采样。

    Args:
        adc: new_adc() 返回的句柄

    Raises:
        Exception: 启动失败时抛出异常
    """
    ...


def adc_stop(adc: ADC_Handle) -> None:
    """
    停止 ADC 连续采样。

    Args:
        adc: new_adc() 返回的句柄

    Raises:
        Exception: 停止失败时抛出异常
    """
    ...


def adc_read(adc: ADC_Handle, buf: bytearray) -> int:
    """
    从 ADC 缓冲区读取采样数据到 buf。

    数据格式（每 4 字节一条采样）：
        [31:18] 保留
        [17]    unit   - ADC 单元 (0=ADC1, 1=ADC2)
        [16:13] channel - 通道号
        [12]    保留
        [11:0]  data   - 原始采样值 (0~4095)

    Args:
        adc: new_adc() 返回的句柄
        buf: 用于接收数据的 bytearray 或 memoryview

    Returns:
        int: 实际读取的字节数，无数据时返回 0

    Raises:
        Exception: 读取失败时抛出异常
    """
    ...


def adc_close(adc: ADC_Handle) -> None:
    """
    释放 ADC 资源，关闭后句柄失效。

    Args:
        adc: new_adc() 返回的句柄

    Raises:
        Exception: 释放失败时抛出异常
    """
    ...


def get_adc_cali() -> int:
    """
    查询当前支持的 ADC 校准方案。

    Returns:
        int: scheme_mask 位掩码，表示支持的校准类型
    """
    ...
