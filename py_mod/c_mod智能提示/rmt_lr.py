"""
ESP32 RMT (Remote Control) 底层驱动模块 - 针对 MicroPython CModule 优化。
支持 DMA 模式、自定义符号数据以及异步发送状态管理。
"""

from typing import Tuple, List, Union

# 类型别名：实际上是 C 层的 rmt_obj_t 指针地址
RMT_Handle = int 

def new(
    gpio: int, data_num: int, data_len: int, mem_block_symbols: int, dma: bool
) -> Tuple[RMT_Handle, List[bytearray]]:
    """
    初始化一个新的 RMT 发送通道并预分配 DMA 内存。

    :param gpio: 输出引脚编号。
    :param data_num: 预分配的缓冲区数量。
    :param data_len: 每个缓冲区包含的符号数量 (rmt_symbol_word_t)。
    :param mem_block_symbols: 硬件通道内存块大小 (通常为 64)。
    :param dma: 是否启用 DMA 模式。
    :return: (rmt_handle, buffer_list)
    """
    ...

def send(
    rmt_handle: RMT_Handle, data: Union[bytearray, bytes, memoryview], length: int
) -> None:
    """
    通过指定的 RMT 通道发送数据。非阻塞操作。

    :param rmt_handle: 句柄地址。
    :param data: 符号数据缓冲区。
    :param length: 要发送的符号个数 (注意不是字节数)。
    """
    ...

def get_free(rmt_handle: RMT_Handle) -> int:
    """
    获取当前已完成发送的缓冲区计数 (空闲计数)。
    该值在 C 层中断回调函数 (on_trans_done) 中自增。

    :return: 当前可用的空闲资源数量。
    """
    ...

def sub_free(rmt_handle: RMT_Handle, val: int) -> None:
    """
    手动减去指定的空闲计数。
    通常在调用 send() 后，调用 sub_free(handle, 1) 来标记一个缓冲区已被占用。

    :param val: 要减去的数值 (通常为 1)。
    """
    ...

def get_symbol_size() -> int:
    """
    获取单个 RMT 符号 (rmt_symbol_word_t) 占用的字节数。
    ESP32 上固定为 4 字节。
    """
    ...

def stop(rmt_handle: RMT_Handle) -> None:
    """
    禁用 RMT 通道。
    """
    ...

def del_encoder(rmt_handle: RMT_Handle) -> None:
    """
    释放 RMT 编码器资源。
    """
    ...

def del_channel(rmt_handle: RMT_Handle) -> None:
    """
    注销并删除 RMT 通道，释放硬件资源。
    """
    ...