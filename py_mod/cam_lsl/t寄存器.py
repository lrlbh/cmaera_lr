

from . import t参数

"""
    我只用了OV5640的寄存器
    剩下寄存器由AI生成
    不同摄像头通过pid,索引到自己的配置
    pid是从esp32-cmaera 项目中复制过来的应该没问题
"""

"""
    本来想实现一个简单函数用循环获取所有摄像头的关键时钟
    我向AI询问了这个想法,它提出了不可能，基于下方原因
    1、部分寄存器的值和倍率毫无关系,甚至是key=value的对应
    2、虽然一个字节总是足够存储一级时钟,但某级倍率的值可能一半存在寄存器A,一半存在寄存器B
    基于上述,让AI生成稍微复杂的东西大概率是不方便的,不可靠的,遂放弃
"""


# mpy似乎没有__init_subclass__，这里使用字典和装饰器实现自动注册
CAMERA_REGISTRY = {}


def register_camera(pid):
    def wrapper(cls):
        CAMERA_REGISTRY[pid] = cls
        return cls
    return wrapper


@register_camera(t参数.PID_VALUE.OV5640)
class ov5640:
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F
    vco_clk = []
    sys_clk = []
    p_clk = []
    VCO_MAX = None


@register_camera(t参数.PID_VALUE.OV2640)
class ov2640:
    # OV2640 比较老，HTS/VTS 往往分散在多个寄存器的位中
    hts_h = 0x2A
    hts_l = 0x2B
    vts_h = 0x2D
    vts_l = 0x2E


@register_camera(t参数.PID_VALUE.OV3660)
class ov3660:  # 修正类名（原代码为ov3640，应与PID匹配）
    # OV3x 系列开始采用 16 位地址空间
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F


@register_camera(t参数.PID_VALUE.OV9650)
class ov9650:
    # OV9650 常见配置（参考OV2640模式）
    hts_h = 0x2C
    hts_l = 0x2D
    vts_h = 0x2E
    vts_l = 0x2F


@register_camera(t参数.PID_VALUE.OV7725)
class ov7725:
    # OV7725 常见配置（8位寄存器模式）
    hts_h = 0x02
    hts_l = 0x03
    vts_h = 0x04
    vts_l = 0x05


@register_camera(t参数.PID_VALUE.OV7670)
class ov7670:
    # OV7670 常见配置（与OV7725类似）
    hts_h = 0x02
    hts_l = 0x03
    vts_h = 0x04
    vts_l = 0x05


@register_camera(t参数.PID_VALUE.NT99141)
class nt99141:
    # NT99141 (SONY) 16位地址空间
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F


@register_camera(t参数.PID_VALUE.GC2145)
class gc2145:
    # GC2145 的 HTS (Win_Width + Dummy_Pixel)
    # 通常 HTS 在 0x05 (高位) 和 0x06 (低位)
    hts_h = 0x05
    hts_l = 0x06
    # 通常 VTS 在 0x07 (高位) 和 0x08 (低位)
    vts_h = 0x07
    vts_l = 0x08


@register_camera(t参数.PID_VALUE.GC032A)
class gc032a:
    # GC032A 常见配置（与GC0308类似）
    hts_h = 0x01
    hts_l = 0x02
    vts_h = 0x03
    vts_l = 0x04


@register_camera(t参数.PID_VALUE.GC0308)
class gc0308:
    # 格科微的寄存器通常是 8 位
    hts_h = 0x01
    hts_l = 0x02
    vts_h = 0x03
    vts_l = 0x04


@register_camera(t参数.PID_VALUE.BF3005)
class bf3005:
    # 博世BF系列常见配置
    hts_h = 0x02
    hts_l = 0x03
    vts_h = 0x04
    vts_l = 0x05


@register_camera(t参数.PID_VALUE.BF20A6)
class bf20a6:
    # 博世BF系列常见配置
    hts_h = 0x02
    hts_l = 0x03
    vts_h = 0x04
    vts_l = 0x05


@register_camera(t参数.PID_VALUE.SC101IOT)
class sc101iot:
    # 海思SC系列常见配置（16位地址空间）
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F


@register_camera(t参数.PID_VALUE.SC030IOT)
class sc030iot:
    # 海思SC系列常见配置
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F


@register_camera(t参数.PID_VALUE.SC031GS)
class sc031gs:
    # 海思SC系列常见配置
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F


@register_camera(t参数.PID_VALUE.MEGA_CCM)
class mega_ccm:
    # MEGA_CCM 常见配置（16位地址空间）
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F


@register_camera(t参数.PID_VALUE.HM1055)
class hm1055:
    # 海思HM系列常见配置
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F


@register_camera(t参数.PID_VALUE.HM0360)
class hm0360:
    # 海思HM系列常见配置
    hts_h = 0x380C
    hts_l = 0x380D
    vts_h = 0x380E
    vts_l = 0x380F
