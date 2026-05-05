"""
rmt_lr 模块 - 基于 ESP32 RMT 驱动的高性能 8bit 信号编码与发送模块。
提供带有渐变填充功能的 RMT 发送支持。
"""

from typing import Union


def new_rmt(
    gpio: int,
    queue_len: int,
    mem_block_symbols: int,
    dma: bool,
    intr_priority: int,
    is_od: bool,
    encode_id: int,
    max_dpi: int,
    symbol_loop: int,
    padding_time_us: int,
    padding_0_xxx: int,
) -> int:
    """
    创建并初始化一个新的 RMT 通道。

    :param gpio: RMT 输出引脚编号
    :param queue_len: 发送队列深度，允许排队的波形组数
    :param mem_block_symbols: RMT 通道硬件缓存符号数 (DMA下最大2046)
    :param dma: 是否开启 DMA 模式 (True/False)
    :param intr_priority: 中断优先级 (0 表示自动分配低优先级)
    :param is_od: 是否为开漏模式 (True 为开漏, False 为推挽)
    :param encode_id: 编码器类型 (1: Copy, 2: Simple 8bit)
    :param max_dpi: DAC 分辨率/周期总 tick 数
    :param symbol_loop: 每字节数据重复多少个 RMT 符号
    :param padding_time_us: 头部/尾部渐变填充的总时长 (微秒)
    :param padding_0_xxx: 渐变填充的占空比千分比 (0~1000)
    :return: 指向 rmt_obj_t 结构体的地址（句柄），供后续函数使用
    """
    ...


def rmt_send(
    rmt_handle: int, data: Union[bytes, bytearray, memoryview], data_len: int
) -> None:
    """
    向指定的 RMT 通道异步发送数据。

    :param rmt_handle: new_rmt 返回的句柄
    :param data: 待发送的数据缓冲区
    :param data_len: 要发送的数据长度
    :raises Exception: 发送失败或队列已满且配置为非阻塞时抛出
    """
    ...


def rmt_get_symbol_size() -> int:
    """
    获取单个 RMT 符号 (rmt_symbol_word_t) 占用的字节大小。
    通常为 4 字节。
    """
    ...


def rmt_stop_channel(rmt_handle: int) -> None:
    """
    禁用指定的 RMT 通道。建议在释放前调用。
    """
    ...


def rmt_delete_encoder(rmt_handle: int) -> None:
    """
    释放与通道绑定的编码器资源。
    """
    ...


def rmt_delete_channel(rmt_handle: int) -> None:
    """
    释放 RMT 通道硬件资源并注销回调。
    """
    ...


def rmt_get_free(rmt_handle: int) -> int:
    """
    获取发送完成的计数（由中断回调累加）。
    用于 Python 层判断发送状态或回收内存。
    """
    ...


def rmt_sub_free(rmt_handle: int, val: int) -> None:
    """
    原子地减去发送完成计数。通常在 Python 处理完一组数据后调用。

    :param rmt_handle: new_rmt 返回的句柄
    :param val: 需要减去的值
    """
    ...


def rmt_close(rmt_handle: int) -> None:
    """
    一键释放所有资源，包括通道、编码器及内部申请的内存。
    """
    ...
