from . import LCD


class 波形:
    # size == 宽 * 高 * 单像素字节
    # 只为存储像素设置，所以不必当心单次append超出环形结构
    def __init__(
        self,
        st: LCD,
        w起点: int,
        h起点: int,
        size_w: int,
        size_h: int,
        多少格: int,
        波形像素: list,
        data_min: list,
        data_max: list,
        波形色: list,
        背景色: bytes,
    ):
        self._st = st
        self._size_byte = len(背景色)
        self._size_h = size_h
        self._size_w = size_w
        self._w起点 = w起点
        self._h起点 = h起点
        self._w终点 = w起点 + size_w - 1
        self._h终点 = h起点 + size_h - 1
        self._波形像素 = 波形像素
        self._波形len = []
        for t in 波形像素:
            self._波形len.append(t * self._size_byte)
        self._波形色 = 波形色
        self._背景色 = 背景色
        self._size = int(size_w * size_h * self._size_byte)
        self._buf = bytearray(self._size)
        self._mv = memoryview(self._buf)
        self._当前下标 = 0  # 最旧字节位置
        self._多少格 = 多少格
        self._min = data_min
        self._max = data_max
        self._允许的最大下标 = []
        self._td = bytearray(self._背景色 * self._size_h)
        for t in 波形像素:
            self._允许的最大下标.append(self._size_h - t)
        self._上一次波形坐标 = [0, 0, 0, 0]

    def 更新(self):
        self._st._set_window(self._w起点, self._h起点, self._w终点, self._h终点)
        if self._当前下标 != self._size:
            self._st._write_data_bytes(self._mv[self._当前下标: self._size])
        if self._当前下标 > 0:
            self._st._write_data_bytes(self._mv[0: self._当前下标])

    def append_data(self, data: list) -> None:
        # 生成背景色
        self._td[:] = self._背景色 * self._size_h
        # self._td = bytearray(self._背景色 * self._size_h)

        # 模拟网格，看看效果
        # for i in  range(5):
        #     if self._当前下标 ==  30 * i * 300:
        #         td = bytearray(self._st.color.基础灰阶.黑 * self._size_h)
        # for i in  range(4):
        #     i = i+1
        #     td[i*60:i*60+3] = self._st.color.基础灰阶.黑

        # 遍历多个输入通道
        还原i = []
        for 通道_i in range(len(data)):
            # 数据映射到下标
            index = (
                (data[通道_i] - self._min[通道_i])
                / (self._max[通道_i] - self._min[通道_i])
                * self._允许的最大下标[通道_i]
            )

            # 限幅，防止传入数据超过幅值
            if index > self._允许的最大下标[通道_i]:
                index = self._允许的最大下标[通道_i]
            if index < 0:
                index = 0

            # 当前波形多少像素做一下偏移
            index = int(index) * self._size_byte
            inedx_p = index + self._波形len[通道_i]
            还原i.append(index)

            # 数据更新到背景色中
            self._td[index:inedx_p] = self._波形色[通道_i] * self._波形像素[通道_i]

            # 剧烈波动，上升接线
            zz = index - self._上一次波形坐标[通道_i]
            zz //= self._size_byte
            if zz > 0:
                self._td[self._上一次波形坐标[通道_i]: index] = (
                    self._波形色[通道_i] * zz
                )

            # 剧烈波动，下降接线
            zz = self._上一次波形坐标[通道_i] - index
            zz //= self._size_byte
            if zz > 0:
                # 下降接线时，是否补头
                # self._td[
                #     self._上一次波形坐标[通道_i] : self._上一次波形坐标[通道_i]
                #     + self._波形len[通道_i]
                # ] = self._波形色[通道_i] * 5
                self._td[index: self._上一次波形坐标[通道_i]] = (
                    self._波形色[通道_i] * zz
                )

        # # 查看有无，不合理数据
        # if len(self._td) != self._size_h * self._size_byte:
        #     udp.send("ERROR")
        #     return

        self._上一次波形坐标 = 还原i
        self._append(self._td)

    # 单次追加数据越多越慢
    def _append(self, data: bytes) -> None:
        if self._当前下标 == self._size:
            self._当前下标 = 0

        for i in range(len(data)):
            self._buf[self._当前下标 + i] = data[i]

        self._当前下标 = self._当前下标 + len(data)
        # udp.send(self.当前下标 )

    # 非常快,不过未知原因当byteaary末尾数据越多越慢
    # 环形内存一次性申请460K+内存,分320还是480次添加忘了
    # 索引起步时添加数据20ms,索引末尾时添加数据0ms，线性降低
    # 上面方法稳定6~7ms，稳定的慢
    # 正常使用应该下面这个快
    # 万一性能不够，整合两个函数为一个
    def _append_mv(self, data: bytes) -> None:
        if self._当前下标 == self._size:
            self._当前下标 = 0
        下一次下标 = self._当前下标 + len(data)
        self._buf[self._当前下标: 下一次下标] = data
        self._当前下标 = 下一次下标

    def _get_all_data(self):
        return self._mv[self._当前下标: self._size], self._mv[0: self._当前下标]



import time
from . import LCD


class 字符区域:
    def __init__(
        self,
        字符串,
        size,
        st: LCD,
        超时,
        x=None,
        y=None,
        字体色=None,
        背景色=None,
        缓存=False,
    ):
        self._超时 = 超时
        self._字体色 = 字体色
        self._背景色 = 背景色
        self._st = st
        self._size = size
        self._x_start = []
        # self._非更新 = ["",0]

        # 起点
        self._x = x
        self._y = y
        if x is None or y is None:
            if st._wh is None:
                self._x = 0
                self._y = 0
            else:
                self._x = st._wh[0]
                self._y = st._wh[1]

        # 终点
        w = self._x
        h = self._y + size
        for 字符 in 字符串:
            self._x_start.append(w)
            if ord(字符) < 128:
                w += size // 2
            else:
                w += size

        if self._st._max_h < h:
            self._st._max_h = h

        # 超区域
        if w > st._width:
            raise ValueError(f"超出显示区域->宽({w})")
        if h > st._height:
            raise ValueError(f"超出显示区域->高({h})")

        # 下次坐标
        # udp.send(f"{w, h}")
        if w >= st._width and h >= self._st._max_h:
            st._wh = (0, h)
        elif w >= st._width:
            st._wh = (self._x, h)
        else:
            st._wh = (w, h - size)

        self._st.txt(字符串, self._x, self._y, size, 字体色, 背景色, 缓存)

    def up_data(self, 字符串, start, 字体色=None, 背景色=None, 缓存=True):
        if 字体色 is None:
            字体色 = self._字体色
        if 背景色 is None:
            背景色 = self._背景色
        self._st.txt(
            字符串,
            self._x_start[start],
            self._y,
            self._size,
            字体色,
            背景色,
            缓存,
        )

    # 比较常用字符串用元组或者列表替代
    # [0] 存数据 [1] 存ms时间戳
    def up_data_time(self, 元组, start, 背景色=None, 缓存=True):
        if 背景色 is None:
            背景色 = self._背景色

        if time.ticks_diff(time.ticks_ms(), 元组[1]) > self._超时:
            字体色 = self._st.color.黄
        else:
            字体色 = self._st.color.绿
        self._st.txt(
            元组[0],
            self._x_start[start],
            self._y,
            self._size,
            字体色,
            背景色,
            缓存,
        )
