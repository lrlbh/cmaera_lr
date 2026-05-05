import asyncio
import time
import rmt_lr


class RMT:
    def __init__(
        self,
        gpio,
        buf_size=1024 * 100,
        buf_num=2,
        gpio缓存数=2046,
        dma=True,
        中断优先级=0,
        开漏=False,
        编码器=2,  # 1=copy,2=8bit
        max_dpi=255,  # dac分辨率最大值
        填充多少us=2400,  # 0~100的单边时间
        填充缓存最大值=666,  #  千分比
        freq_khz=20,
        轮询间隔ms=5,
    ):
        self.free了没 = True
        self.轮询间隔ms = 轮询间隔ms

        # 计算每个dac数据需要维持多少个周期
        self.tick_ns = 12.5  # 每个分辨率多少ns
        self.tick_ns = 12.5 / 1_000_000_000  # 修正单位为秒
        freq_khz *= 1000
        每个字节重复多少周期 = 1 / (freq_khz * (max_dpi * self.tick_ns))
        每个字节重复多少周期 = round(每个字节重复多少周期)
        self.rmt = rmt_lr.new_rmt(
            gpio,
            buf_num,
            gpio缓存数,
            dma,
            中断优先级,
            开漏,
            编码器,
            max_dpi,
            每个字节重复多少周期,
            填充多少us,
            填充缓存最大值,
        )

        # 使用中内存
        self.send_mem = []

        # 可以分配内存
        self.null_mem = []
        for _ in range(buf_num):
            self.null_mem.append(bytearray(buf_size))

        self.free了没 = False

    def get_mem(self) -> bytearray:
        while True:
            可回收内存 = rmt_lr.rmt_get_free(self.rmt)

            for _ in range(可回收内存):
                self.null_mem.append(self.send_mem.pop(0))
            rmt_lr.rmt_sub_free(self.rmt, 可回收内存)

            if len(self.null_mem) > 0:
                return self.null_mem.pop(0)

            time.sleep_ms(self.轮询间隔ms)

    async def get_mem_async(self, sleep_ms=10) -> bytearray:
        while True:
            可回收内存 = rmt_lr.rmt_get_free(self.rmt)
            for _ in range(可回收内存):
                self.null_mem.append(self.send_mem.pop(0))
            rmt_lr.rmt_sub_free(self.rmt, 可回收内存)

            if len(self.null_mem) > 0:
                return self.null_mem.pop(0)

            await asyncio.sleep_ms(self.轮询间隔ms)

    # 长度需要用字节数,不能用数据个数
    def return_mem(self, data: bytearray, data_len: int = None, 忽略零长度=True):

        # 拦截已知错误，发送数据长度为
        # 默认寂寞处理该错误
        if data_len == 0 and 忽略零长度:
            # 不发送，直接放回空闲列表
            self.null_mem.append(data)
            return

        if data_len is None:
            data_len = len(data)
        self.send_mem.append(data)
        rmt_lr.rmt_send(self.rmt, data, data_len)

    def close(self):
        if self.free了没:
            return
        rmt_lr.rmt_close(self.rmt)
        self.send_mem.clear()
        self.null_mem.clear()
        self.free了没 = True

    def __del__(self):
        self.close()
