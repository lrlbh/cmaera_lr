"""
MicroPython RMT LR 驱动模块
提供基于 ESP32 RMT 外设的自定义编码与发送功能。
"""

from typing import Union


def new_rmt(
    gpio: int,
    queue_len: int,
    mem_block_symbols: int,
    dma: int,
    intr_priority: int,
    is_od: int,
    encode_id: int,
    dac_max: int,
    symbol_loop: int,
    hed_symbol: int,
    end_symbol: int,
) -> int:
    """
    创建并初始化 RMT 通道。

    :param gpio: RMT 输出引脚编号
    :param queue_len: 发送队列深度
    :param mem_block_symbols: RMT 内存块符号数量 (DMA模式下建议2046)
    :param dma: 是否开启 DMA (1开启, 0关闭)
    :param intr_priority: 中断优先级 (0-3)
    :param is_od: 是否为开漏模式 (1开漏, 0推挽)
    :param encode_id: 编码器 ID (1: Copy Encoder, 2: Simple/8bit Encoder)
    :param dac_max: DAC 分辨率/最大值
    :param symbol_loop: 每个字节对应的符号循环次数
    :param hed_symbol: 头部填充的符号数量
    :param end_symbol: 尾部填充的符号数量
    :return: 返回 rmt_obj_t 结构体的内存地址指针 (int)
    """
    ...


def rmt_send(
    rmt_ptr: int, data: Union[bytes, bytearray, memoryview], data_len: int
) -> None:
    """
    通过指定的 RMT 通道发送数据。

    :param rmt_ptr: new_rmt 返回的通道指针
    :param data: 待发送的数据缓存
    :param data_len: 编码的数据长度
    """
    ...


def rmt_get_symbol_size() -> int:
    """
    获取底层 rmt_symbol_word_t 结构体的大小（单位：字节）。
    """
    ...


def rmt_stop_channel(rmt_ptr: int) -> None:
    """
    停止 RMT 通道传输并禁用。
    """
    ...


def rmt_delete_encoder(rmt_ptr: int) -> None:
    """
    释放编码器资源。
    """
    ...


def rmt_delete_channel(rmt_ptr: int) -> None:
    """
    删除 RMT 通道并释放资源。
    """
    ...


def rmt_get_free(rmt_ptr: int) -> int:
    """
    获取发送完成的计数（由 C 层的 rmt_on_transmit_done 累加）。
    """
    ...


def rmt_sub_free(rmt_ptr: int, val: int) -> None:
    """
    减去已处理的空闲计数。
    """
    ...
