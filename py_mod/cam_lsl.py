import cameralr


class t图片分辨率:
    """
    图像尺寸枚举类 (由 C 语言枚举转换)
    索引从 0 开始递增
    """
    # 基础尺寸
    t_96x96 = 0
    t_160x120 = 1   # QQVGA
    t_128x128 = 2
    t_176x144 = 3   # QCIF
    t_240x176 = 4   # HQVGA
    t_240x240 = 5
    t_320x240 = 6   # QVGA
    t_320x320 = 7
    t_400x296 = 8   # CIF
    t_480x320 = 9   # HVGA

    # 标准尺寸
    t_640x480 = 10  # VGA
    t_800x600 = 11  # SVGA
    t_1024x768 = 12  # XGA
    t_1280x720 = 13  # HD
    t_1280x1024 = 14  # SXGA
    t_1600x1200 = 15  # UXGA

    # 3MP 传感器
    t_1920x1080 = 16  # FHD
    t_720x1280 = 17  # P_HD
    t_864x1536 = 18  # P_3MP
    t_2048x1536 = 19  # QXGA

    # 5MP 传感器
    t_2560x1440 = 20  # QHD
    t_2560x1600 = 21  # WQXGA
    t_1080x1920 = 22  # P_FHD
    t_2560x1920 = 23  # QSXGA
    t_2592x1944 = 24  # 5MP

    t_invalid = 25


class t图片格式:
    """
    统一的图片格式类
    包含：分辨率尺寸 (size) 和 像素格式 (pixformat)
    """

    # --- 1. 像素格式 (Pixel Format) ---
    # 按照 C 语言枚举顺序，从 0 开始
    rgb565 = 0   # 2BPP/RGB565
    yuv422 = 1   # 2BPP/YUV422
    yuv420 = 2   # 1.5BPP/YUV420
    grayscale = 3   # 1BPP/GRAYSCALE
    jpeg = 4   # JPEG/COMPRESSED
    rgb888 = 5   # 3BPP/RGB888
    raw = 6   # RAW
    rgb444 = 7   # 3BP2P/RGB444
    rgb555 = 8   # 3BP2P/RGB555
    raw8 = 9   # RAW 8-bit


class t内存位置:
    psram = 0
    dram = 1


class cam:
    def __init__(
        self,
        data_0_7=[21, 48, 45, 47, 14, 12, 11, 9], p_clk=13,
        sda=7, scl=15,
        vsync=17, href=8,
        pwdn=-1, rst=-1, xclk=-1,
        xclk_freq=24_000_000, xclk_pwm_控制器=0, xclk_pwm_通道=0,
        t图片格式=t图片格式.jpeg, t图片分辨率=t图片分辨率.t_2592x1944,
        t图片质量=12, t缓冲区个数=2,
        t内存位置=t内存位置.psram, t最新帧=False, i2c_控制器=0
    ):
        # 只保存成员变量，不操作摄像头
        self.data_0_7 = data_0_7
        self.p_clk = p_clk
        self.sda = sda
        self.scl = scl
        self.vsync = vsync
        self.href = href
        self.pwdn = pwdn
        self.rst = rst
        self.xclk = xclk
        self.xclk_freq = xclk_freq
        self.xclk_pwm_控制器 = xclk_pwm_控制器
        self.xclk_pwm_通道 = xclk_pwm_通道
        self.t图片格式 = t图片格式
        self.t图片分辨率 = t图片分辨率
        self.t图片质量 = t图片质量
        self.t缓冲区个数 = t缓冲区个数
        self.t内存位置 = t内存位置
        self.t最新帧 = t最新帧
        self.i2c_控制器 = i2c_控制器

        self._buf_p = None
        self.rstart()

    # 修改成员变量需要重新初始化摄像头
    def rstart(self):
        # 真正初始化摄像头
        cameralr.deinit()
        cameralr.init({
            "pin_pwdn": self.pwdn,
            "pin_reset": self.rst,
            "pin_xclk": self.xclk,
            "pin_sccb_sda": self.sda,
            "pin_sccb_scl": self.scl,
            "pin_d7": self.data_0_7[7],
            "pin_d6": self.data_0_7[6],
            "pin_d5": self.data_0_7[5],
            "pin_d4": self.data_0_7[4],
            "pin_d3": self.data_0_7[3],
            "pin_d2": self.data_0_7[2],
            "pin_d1": self.data_0_7[1],
            "pin_d0": self.data_0_7[0],
            "pin_vsync": self.vsync,
            "pin_href": self.href,
            "pin_pclk": self.p_clk,
            "xclk_freq_hz": self.xclk_freq,
            "ledc_timer": self.xclk_pwm_控制器,
            "ledc_channel": self.xclk_pwm_通道,
            "pixel_format": self.t图片格式,
            "frame_size": self.t图片分辨率,
            "jpeg_quality": self.t图片质量,
            "fb_count": self.t缓冲区个数,
            "fb_location": self.t内存位置,
            "grab_mode": 0 if self.t最新帧 else 1,
            "sccb_i2c_port": self.i2c_控制器,
        })

    def deinit(self):
        cameralr.deinit()

    def _get_pid(self):
        high = cameralr.get_reg(0x300A, 0xFF)
        low = cameralr.get_reg(0x300B, 0xFF)
        return (high << 8) | low

    def af_run(self):
        pid = self._get_pid()
        if pid != 0x5640:
            raise RuntimeError(
                "摄像头不支持自动对焦, 摄像头PID=0x%04X" % pid)
        cameralr.af_run()

    def get_reg(self, reg: int, mask: int):
        return cameralr.get_reg(reg, mask)

    def set_reg(self, reg: int, mask: int, value: int):
        return cameralr.set_reg(reg, mask, value)

    def set_分辨率(self, size: int):
        self.t图片分辨率 = size
        return cameralr.set_img_size(size)

    def set_jepg_质量(self, quality: int):
        self.t图片质量 = quality
        return cameralr.set_jepg_quality(quality)

    def set_水平镜像(self, 镜像: bool):
        return cameralr.set_hmirror(1 if 镜像 else 0)

    def set_垂直翻转(self, 翻转: bool):
        return cameralr.set_vflip(1 if 翻转 else 0)

    def set_pll(self,
                bypass: int,
                mul: int,
                sys: int,
                root: int,
                pre: int,
                seld5: int,
                pclken: int,
                pclk: int
                ) -> int:
        return cameralr.set_pll(bypass, mul, sys, root, pre, seld5, pclken, pclk)

    def set_xclk(self,  xclk: int, timer: int = None):
        self.xclk = xclk
        if timer is None:
            timer = self.xclk_pwm_控制器
        else:
            self.xclk_pwm_控制器 = timer
        return cameralr.set_xclk(timer, xclk)

    def get_img_data(self):
        return cameralr.get_img_data()

    def free_img_p(self):
        if self._buf_p is None:
            return
        cameralr.free_img_p(self._buf_p)
        self._buf_p = None

    def get_img_p(self):
        self.free_img_p()
        d, p = cameralr.get_img_p()
        self._buf_p = p
        return d
