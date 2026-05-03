import asyncio

import adc_lr
import time


# 参数自动化度太低了，分配内存计算合理轮询延迟这些应该是语义自动化的
class ADC_连续:
    def __init__(
        self,
        pins=[],
        attens=[0] * 10,  # 每个通道的衰减  0 = 0dB, 1 = 2.5dB, 2 = 6dB, 3 = 12dB
        bit_widh=[12] * 10,  # 每个通道的位宽 9~13 or 0,0是最大选择最大位宽
        units=[0] * 10,  # 每个通道属于什么单元 单元1
        采样频率=83_333,  # 采样频率,S3支持 611~83K
        每帧大小=4096,  # 帧大小 字节  adc采样延迟
        # 内部会申请5个帧？ 需要是SOC_ADC_DIGI_DATA_BYTES_PER_CONV的整数倍
        buf_size=1024 * 20,  # 内部总空间 字节 最大缓存时间
        sleep_ms=10,
        flush_flag=1,  # 缓冲区满时，0=覆盖，1等于清空
        输出格式=1,  # 1 = type2格式,S3只支持type2格式
        转换模式=1,  # 1=使用adc1,2=使用adc2,3=同时使用ADC1和ADC2,4=交替使用ADC1和ADC2
    ):
        通道 = []  # S3的ADC1，GPIO-1,刚好是adc通道
        for gpio in pins:
            通道.append(gpio - 1)

        self.adc = adc_lr.new_adc(
            通道,
            buf_size,
            每帧大小,
            flush_flag,
            attens,
            units,
            bit_widh,
            采样频率,
            输出格式,
            转换模式,
        )
        self.每帧大小 = 每帧大小
        self.free = False
        self.sleep_ms = sleep_ms

    def start(self, buf_size=None):
        if buf_size is None:
            buf_size = self.每帧大小
        self.buf = bytearray(buf_size)
        adc_lr.adc_start(self.adc)
        return self

    def close(self):
        if not self.free:
            adc_lr.adc_close()
            self.free = True

    def __del__(self):
        self.close()

    def get_data_p(self, read_len=None):
        if read_len is None:
            read_len = self.每帧大小

        buf_v = memoryview(self.buf)[:read_len]
        this_len = 0

        # 循环读取
        while this_len < read_len:
            buf_tmp = buf_v[this_len:]
            this_len += adc_lr.adc_read(self.adc, buf_tmp)
            # lib_lsl.send(this_len)
            time.sleep_ms(self.sleep_ms)

        if this_len == read_len:  # 读取到了合法长度
            return buf_v
        else:  # 读取到了非法长度
            raise Exception(f"读取到了非法长度: {read_len}{this_len}")

    async def get_data_p_async(self, read_len=None):
        if read_len is None:
            read_len = self.每帧大小

        buf_v = memoryview(self.buf)[:read_len]
        this_len = 0

        # 循环读取
        while this_len < read_len:
            buf_tmp = buf_v[this_len:]
            this_len += adc_lr.adc_read(self.adc, buf_tmp)
            # lib_lsl.send(this_len)
            asyncio.sleep_ms(self.sleep_ms)

        if this_len == read_len:  # 读取到了合法长度
            return buf_v
        else:  # 读取到了非法长度
            raise Exception(f"读取到了非法长度: {read_len}{this_len}")
