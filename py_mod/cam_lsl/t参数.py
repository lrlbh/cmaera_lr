class PID_VALUE:
    OV9650 = 0x96
    OV7725 = 0x77
    OV2640 = 0x26
    OV3660 = 0x3660
    OV5640 = 0x5640
    OV7670 = 0x76
    NT99141 = 0x1410
    GC2145 = 0x2145
    GC032A = 0x232a
    GC0308 = 0x9b
    BF3005 = 0x30
    BF20A6 = 0x20a6
    SC101IOT = 0xda4a
    SC030IOT = 0x9a46
    SC031GS = 0x0031
    MEGA_CCM =0x039E
    HM1055 = 0x0955
    HM0360 = 0x0360


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
