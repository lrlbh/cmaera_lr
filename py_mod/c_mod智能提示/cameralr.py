# cameralr.pyi
# MicroPython user C module - camera

from typing import Tuple

# ----------------------------
# 初始化 / 反初始化
# ----------------------------


def init(config: dict) -> None:
    """
    初始化摄像头

    config 字典必须包含：
        pin_pwdn: int
        pin_reset: int
        pin_xclk: int
        pin_sccb_sda: int
        pin_sccb_scl: int
        pin_d7: int
        pin_d6: int
        pin_d5: int
        pin_d4: int
        pin_d3: int
        pin_d2: int
        pin_d1: int
        pin_d0: int
        pin_vsync: int
        pin_href: int
        pin_pclk: int
        xclk_freq_hz: int
        ledc_timer: int
        ledc_channel: int
        pixel_format: int
        frame_size: int
        jpeg_quality: int
        fb_count: int
        fb_location: int
        grab_mode: int
        sccb_i2c_port: int
    """
    ...


def deinit() -> None:
    """释放摄像头资源"""
    ...

# ----------------------------
# 寄存器操作
# ----------------------------


def set_reg(reg: int, mask: int, value: int) -> int:
    """设置寄存器"""
    ...


def get_reg(reg: int, mask: int) -> int:
    """读取寄存器"""
    ...

# ----------------------------
# 图像设置
# ----------------------------


def set_img_size(size: int) -> int:
    """设置分辨率"""
    ...


def set_jepg_quality(quality: int) -> int:
    """设置 JPEG 质量"""
    ...


def set_hmirror(enable: int) -> int:
    """水平镜像"""
    ...


def set_vflip(enable: int) -> int:
    """垂直翻转"""
    ...

# ----------------------------
# 时钟设置
# ----------------------------


def set_pll(
    bypass: int,
    mul: int,
    sys: int,
    root: int,
    pre: int,
    seld5: int,
    pclken: int,
    pclk: int
) -> int:
    """配置 PLL"""
    ...


def set_xclk(timer: int, xclk: int) -> int:
    """设置输入时钟"""
    ...

# ----------------------------
# 自动对焦
# ----------------------------


def af_run() -> None:
    """执行自动对焦"""
    ...

# ----------------------------
# 图像获取
# ----------------------------


def get_img_data() -> bytes:
    """
    获取图像数据（安全，拷贝）
    返回 JPEG bytes
    """
    ...


def get_img_p() -> Tuple[memoryview, int]:
    """
    获取图像零拷贝数据
    返回:
        (memoryview, frame_buffer_pointer)
    必须调用 free_img_p(ptr)
    """
    ...


def free_img_p(ptr: int) -> None:
    """释放零拷贝 frame buffer"""
    ...


def get_pid() -> int:
    """获取摄像头pid"""
    ...
