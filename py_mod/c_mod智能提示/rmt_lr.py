"""
RMT (Remote Control Peripheral) Low-level Runner 模块
该模块提供了对 ESP32 RMT 硬件的底层控制，支持自定义编码器回调以实现连续、不间断的数据传输。
"""

from typing import Tuple, Union

# 这里的类型标注模拟了 MicroPython 的 bytearray 或读写 buffer 协议
Buffer = Union[bytearray, memoryview, bytes]


def new_rmt(
    gpio: int, data_len: int, gpio_cache: int, dma: int, intr_priority: int, is_od: int
) -> Tuple[int, bytearray]:
    """
    创建一个新的 RMT 发送通道并初始化。

    :param gpio: 输出引脚编号 (GPIO Number)
    :param data_len: 申请的 DMA 共享内存缓冲区大小（字节）
    :param gpio_cache: RMT 硬件通道的内存块符号数 (mem_block_symbols)，通常为 48 或 64 的倍数
    :param dma: 是否启用 DMA (1 为启用, 0 为禁用)
    :param intr_priority: 中断优先级 (0-3，0 为自动分配)
    :param is_od: 是否开启开漏模式 (1 为开漏, 0 为推挽)
    :return: 一个元组 (rmt_ptr_address, shared_buffer)
             - rmt_ptr_address: RMT 对象的 C 指针地址（整数）
             - shared_buffer: 分配的 bytearray，用于存放 RMT 符号数据
    """
    ...


def rmt_loop(rmt_ptr: int, data: Buffer, data_len: int) -> None:
    """
    触发 RMT 发送循环。

    :param rmt_ptr: new_rmt 返回的对象指针地址
    :param data: 包含 rmt_symbol_word_t 数据的缓冲区
    :param data_len: 要发送的数据字节长度
    """
    ...


def rmt_get_symbol_size() -> int:
    """
    获取单个 RMT 符号 (rmt_symbol_word_t) 占用的字节数。
    通常在 ESP32 上为 4 字节。
    """
    ...


def rmt_stop_channel(rmt_ptr: int) -> None:
    """
    停止 RMT 通道传输并使能禁用硬件。
    """
    ...


def rmt_delete_encoder(rmt_ptr: int) -> None:
    """
    删除并释放编码器资源。
    """
    ...


def rmt_delete_channel(rmt_ptr: int) -> None:
    """
    释放 RMT 通道硬件资源。
    """
    ...
