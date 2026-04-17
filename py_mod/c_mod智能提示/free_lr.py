"""
内存释放辅助模块 (free_lr)
专门用于手动释放 C 层通过 malloc 或 heap_caps_malloc 申请的非 GC 管理内存。
"""


def free_lr(address: int) -> None:
    """
    释放由标准 malloc 申请的内存。

    :param address: 内存块的起始地址（通常从 rmt_obj 指针或 bytearray 的内部缓冲区获取）。
    """
    ...


def heap_caps_free_bytearray_lr(address: int) -> None:
    """
    释放由 ESP-IDF heap_caps_malloc 申请的特定类型内存（如 MALLOC_CAP_DMA）。
    在释放 new_rmt 返回的 list 中的 bytearray 内部内存时，应使用此函数。

    :param address: 内存块的起始地址。
    """
    ...
