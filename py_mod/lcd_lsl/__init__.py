
# 导出类，少一级访问路径,内部不生效
# 注意顺序
from lcd.预设色 import 预设色16位, 预设色24位
from .lcd import LCD
from .辅助显示功能 import 字符区域, 波形




from .gc9107 import GC9107
from .gc9a01 import GC9A01
from .ili9488 import ILI9488
from .nv3007 import NV3007
from .st7796 import ST7796
from .st7796便宜 import ST7796便宜
from .st7365傻 import ST7365傻


__all__ = ['预设色16位', '预设色24位']
