import asyncio

import time

import free_lr
import rmt_lr


# BUG
# 1、测试内存分配在PSRAM上的效果,SRAM比较小,网络数据量接近带宽时,缓存小了容易抖
#   a、heap_caps_malloc(buffer_size, MALLOC_CAP_DMA);
# 2、__del__不会执行，先不管，手动释放一下就行了
# 3、编码器
#   a、自带的copy编码器是否存在cpu浪费问题
#   b、需要实现一个分辨率编码器，减少数据量，但不知道会不会过于浪费cpu了
# 5、DMA发送通道只有一个，部分型号一个都没有
#   a、在cmod中而外维护一下通道，避免mpy忘记close,导致下次没有通道可以用了
#   b、可靠的close
#   c、回到问题2
# 6、更细腻的资源释放,new_rmt失败,必然存在资源申请了部分的情况
# 7、因为问题5，出现的问题7
#   引脚本身有48个或者几百个缓冲区，如果需要多个引脚，也类似个小dma了应该可以折中一下使用吧？
#   千万要验证，千万要验证，千万要验证，IDF提供的通道同步函数无雷，否则无意义


# 4、即使确保了提前填充每个缓冲区，IDF内部在自动切换缓冲区时，也会有大概20~40us停止输出
#   a、在githu上找证实，这个情况确实存在，该讨论持续多年有人吐槽这个问题
#   b、不过官方最终也没有提供解决
#   c、有人似乎多次提到在IDF4.X中该问题不存在
# 该问题来自不可以用idf实现的代码，那个缓冲区排队根本就是假的，猜测解决办法:
#   设置无限循环，然后只发送一次数据，最后和IDF同时操作同一片内存
#   这片内存搞大一点，在编码器中实时传出大概进度
#   外部维护一个上次设置范围，同时基于大概进度，设置大概安全范围的内存
#   这样应该可以解决这个问题，不过这tm基本要重新实现了，现在才发现，真SB
#   对了，千万别忘记,千万别忘记,千万别忘记测试无限循环发送同样数据时，这个问题是不是真的没了


class RMT:
    def __init__(
        self,
        gpio: int,
        缓冲区长度: int,
        缓冲区数量: int = 2,
        gpio缓存块数量: int = 1024,
        dma: bool = True,
    ):
        # 申请通道，申请编码器，申请内存
        self.资源释放 = False
        self.rmt, self.mem = rmt_lr.new(
            gpio,
            缓冲区长度,
            缓冲区数量,
            gpio缓存块数量,
            dma,
        )
        self.资源释放 = True

        # 单周期占用字节数
        self.symbol_size = rmt_lr.get_symbol_size()

        # 可以分配内存
        self.null_mem = list(self.mem)

        # 发送中内存
        self.send_mem = []

    # 每个周期数据
    # /**
    # * @brief The layout of RMT symbol stored in memory, which is decided by the hardware design
    # */
    # typedef union {
    #     struct {
    #         uint16_t duration0 : 15; /*!< Duration of level0 */
    #         uint16_t level0 : 1;     /*!< Level of the first part */
    #         uint16_t duration1 : 15; /*!< Duration of level1 */
    #         uint16_t level1 : 1;     /*!< Level of the second part */
    #     };
    #     uint32_t val; /*!< Equivalent unsigned value for the RMT symbol */
    # } rmt_symbol_word_t;
    #
    #
    #     32bit
    #         bit 1-15    持续时间
    #         bit 16      高电平 or 低电平
    #         bit 17-31   持续时间
    #         bit 15      高电平 or 低电平
    def get_mem(self, sleep_ms=10) -> bytearray:
        while True:
            可回收内存 = rmt_lr.get_free(self.rmt)
            for _ in range(可回收内存):
                self.null_mem.append(self.send_mem.pop(0))
            rmt_lr.sub_free(self.rmt, 可回收内存)

            if len(self.null_mem) > 0:
                return self.null_mem.pop(0)

            time.sleep_ms(sleep_ms)

    async def get_mem_async(self, sleep_ms=10) -> bytearray:
        while True:
            可回收内存 = rmt_lr.get_free(self.rmt)
            for _ in range(可回收内存):
                self.null_mem.append(self.send_mem.pop(0))
            rmt_lr.sub_free(self.rmt, 可回收内存)

            if len(self.null_mem) > 0:
                return self.null_mem.pop(0)

            await asyncio.sleep_ms(sleep_ms)

    # 长度需要用字节数,不能用数据个数
    def return_mem(self, data: bytearray, data_len: int = None, 忽略零长度=True):

        # 拦截已知错误，发送数据长度为0，默认寂寞处理该错误
        if data_len == 0 and 忽略零长度:
            # 不发送，直接放回空闲列表
            self.null_mem.append(data)
            return

        if data_len is None:
            data_len = len(data)
        self.send_mem.append(data)
        rmt_lr.send(self.rmt, data, data_len)

    # 实验性测试，释放资源出错时抛出错误查看
    # 应该try每个操作，避免后面的资源没有释放
    def close(self):
        # lib_lsl.send("111111111111")
        if self.资源释放:
            # lib_lsl.send("2222222222")

            # 避免多次释放，或者对象没有创建成功也会执行__del__
            self.资源释放 = False

            rmt_lr.stop(self.rmt)

            # 释放编码器
            rmt_lr.del_encoder(self.rmt)

            # 释放通道
            rmt_lr.del_channel(self.rmt)

            # 释放缓冲区
            for mem in self.mem:
                free_lr.heap_caps_free_bytearray_lr(mem)

            # 释放C对象
            free_lr.free_lr(self.rmt)

    def __del__(self):
        self.close()
