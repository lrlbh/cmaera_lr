"""
MicroPython C extension module: tl_lr
"""


def ws_mask_decode(data: bytearray, mask: bytes) -> None:
    """
    WebSocket XOR mask decode.

    data:
        Modified in-place.

    mask:
        4 bytes masking key.
    """
    ...


def ws_mask_decode_2(data: bytearray, mask: bytes) -> None:
    """
    Optimized WebSocket XOR mask decode.

    Uses uint32_t processing internally.
    """
    ...
