import asyncio
import time
import lib_lsl
import rmt_lr
import math


class RMT:
    def __init__(
        self,
        gpio,
        buf_ms=2000,  # 一个buf最大存储多少ms数据
        buf_num=2,  # 几个buf
        freq_khz=20,  # 主要影响传输数据量
        填充多少us=4500,  # 0~100的单边时间
        轮询间隔ms=3,  # 轮询是否有剩余内存
        gpio缓存数=2046,  # DMA情况下影响最大2046
        dma=True,  # DMA可用gpio缓存显著高不少
        中断优先级=0,  # 0是默认,IDF会设置为最低优先级
        开漏=False,  # 引脚可用OD或者PP
        编码器=2,  # 1=copy,2=8bit
        max_dpi=255,  # dac分辨率最大值
        填充缓存最大值=666,  #  千分比
        tick_ns=12.5,  # 每个tick分辨率多少ns
    ):

        self.max_dpi = max_dpi
        self.free了没 = True  # new成功才需要释放
        self.轮询间隔ms = 轮询间隔ms

        # tick单位从ns变s
        self.tick_s = tick_ns / 1_000_000_000  # 修正单位为秒

        # freq单位从khz变hz
        self.freq = freq_khz * 1000

        # 计算8bit编码器,每个dac数据需要维持多少个周期
        self.每个字节重复多少周期 = 1 / (self.freq * (max_dpi * self.tick_s))

        # 申请RMT对象
        self.rmt = rmt_lr.new_rmt(
            gpio,
            buf_num,
            gpio缓存数,
            dma,
            中断优先级,
            开漏,
            编码器,
            max_dpi,
            round(self.每个字节重复多少周期),  # 四舍五入
            填充多少us,
            填充缓存最大值,
        )

        # 使用中内存
        self.send_mem = []

        # 可以分配内存
        self.null_mem = []
        for _ in range(buf_num):
            self.null_mem.append(bytearray(int(buf_ms * self.freq / 1000)))

        self.free了没 = False

    def get_mem(self) -> bytearray:
        while True:
            可回收内存 = rmt_lr.rmt_get_free(self.rmt)
            for _ in range(可回收内存):
                self.null_mem.append(self.send_mem.pop(0))
                rmt_lr.rmt_sub_free(self.rmt, 1)

            if len(self.null_mem) > 0:
                return self.null_mem.pop(0)

            time.sleep_ms(self.轮询间隔ms)

    async def get_mem_async(self, sleep_ms=10) -> bytearray:
        while True:
            可回收内存 = rmt_lr.rmt_get_free(self.rmt)
            for _ in range(可回收内存):
                self.null_mem.append(self.send_mem.pop(0))
                rmt_lr.rmt_sub_free(self.rmt, 1)

            if len(self.null_mem) > 0:
                return self.null_mem.pop(0)

            await asyncio.sleep_ms(self.轮询间隔ms)

    # 长度需要用字节数,不能用数据个数
    def return_mem(self, data: bytearray, data_len: int = None, 忽略零长度=True):

        # 拦截已知错误，发送数据长度为0
        # 默认静默处理该错误
        if data_len == 0 and 忽略零长度:
            # 不发送，直接放回空闲列表
            self.null_mem.append(data)
            return

        if data_len is None:
            data_len = len(data)

        self.send_mem.append(data)
        rmt_lr.rmt_send(self.rmt, data, data_len)

    def loop_sine(self, 振幅=0.9, 小于采样率几倍=16):

        # 正弦波频率
        freq = self.freq / 小于采样率几倍
        实际频率倍率 = self.每个字节重复多少周期 / round(self.每个字节重复多少周期)
        实际频率 = 实际频率倍率 * freq

        # 输出参数
        lib_lsl.send("输出正弦波参数")
        lib_lsl.send(
            f"\t采样率:{self.freq / 1000:.2f}Khz ",
            f"设置频率:{freq / 1000:.2f}Khz ",
            f"设置振幅:{振幅 * 100:.2f}% ",
        )
        lib_lsl.send(
            f"\t期望每字节重复次数:{self.每个字节重复多少周期:.2f} ",
            f"实际每字节重复次数:{round(self.每个字节重复多少周期)} ",
            f"实际频率倍率:{实际频率倍率:.2f} ",
            f"实际频率:{实际频率 / 1000:.3f}Khz",
        )
        lib_lsl.send(
            f"\t单个BUF消耗内存:{len(self.null_mem[0]) / 1024:.2f}KiB ",
            f"BUF数量:{len(self.null_mem)} ",
            f"所有BUF消耗内存:{len(self.null_mem[0]) / 1024 * len(self.null_mem):.2f}KiB",
        )

        # 中心点
        中心点 = self.max_dpi / 2
        振幅 = 中心点 * 振幅

        # 生成正弦波
        s_time = time.ticks_ms()
        omega = 2 * math.pi * freq / self.freq
        for i in range(len(self.null_mem[0])):
            # 计算当前点的正弦值，范围在 -1 到 1 之间
            sine_val = math.sin(i * omega)

            # 映射到具体数据
            scaled_val = int(振幅 * sine_val + 中心点)

            # 给每一个BUF耗时
            for data in self.null_mem:
                data[i] = scaled_val

        lib_lsl.send(f"生成信号耗时: {time.ticks_ms() - s_time}ms")

        while True:
            self.return_mem(self.get_mem())

    def close(self):
        if self.free了没:
            return
        rmt_lr.rmt_close(self.rmt)
        self.send_mem.clear()
        self.null_mem.clear()
        self.free了没 = True

    def __del__(self):
        self.close()
