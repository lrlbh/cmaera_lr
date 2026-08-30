import _thread
import time
import random
import lib_lsl
from collections import deque


# 用锁替代sleep,实现阻塞通讯
class Queue:
    def __init__(self, max_len=30, 每个数据处理耗时ms=0.69):
        # 数据结构
        self.max_len = max_len
        self.data = deque((), max_len)

        # 正常不会延迟，只有dqueue数据要溢出了才会触发
        self.满数据时等待时间 = max(3, int(max_len * 每个数据处理耗时ms))

        # 数据锁
        self.lock = _thread.allocate_lock()

        # 阻塞锁
        self.event = _thread.allocate_lock()
        self.event.acquire()

    def append(self, item):
        while True:
            self.lock.acquire()

            if len(self.data) < self.max_len:
                self.data.append(item)

                # 0 -> 1，唤醒消费者
                if len(self.data) == 1:  # append负责,阻塞解锁
                    self.event.release()

                self.lock.release()
                return

            self.lock.release()
            time.sleep_ms(self.满数据时等待时间)

    def popleft(self):
        # 无数据时阻塞
        self.event.acquire()

        self.lock.acquire()

        item = self.data.popleft()

        # 还有数据，唤醒下一个消费者
        if len(self.data) > 0:  # popleft负责,阻塞加锁
            self.event.release()

        self.lock.release()

        return item


# ============================================================
# 测试
# ============================================================


def Queue_test(
    queue_max_len=30,  # queue最大长度
    read_thread_num=9,  # 生产线程数量
    write_thread_num=9,  # 消费线程数量
    thread_data_num=360,  # 每个线程处理多少个数据
):

    # ============================================================
    # 测试参数
    # ============================================================

    # 线程数量
    PRODUCER_NUM = write_thread_num  # 生产
    CONSUMER_NUM = read_thread_num  # 消费

    # 每个生产者生产多少条
    ITEMS_PER_PRODUCER = thread_data_num

    # Queue 最大容量
    QUEUE_MAX_LEN = queue_max_len

    # 模拟线程交错
    PRODUCER_DELAY_MS = 0
    CONSUMER_DELAY_MS = 2

    # Payload 长度
    PAYLOAD_LEN = 64

    # 是否打印每一条数据
    PRINT_EVERY_ITEM = False

    # 随机种子
    RANDOM_SEED = 12345

    random.seed(RANDOM_SEED)

    total = PRODUCER_NUM * ITEMS_PER_PRODUCER

    q = Queue(QUEUE_MAX_LEN)

    # --------------------------------------------------------
    # 统计
    # --------------------------------------------------------

    produce_count = 0
    consume_count = 0

    producer_finished = 0
    consumer_finished = 0

    # --------------------------------------------------------
    # 消费记录
    #
    # (producer_id, sequence)
    #
    # 用于检查：
    #   重复
    #   丢失
    # --------------------------------------------------------

    consumed = {}

    # --------------------------------------------------------
    # 错误统计
    # --------------------------------------------------------

    corrupt_count = 0
    duplicate_count = 0
    queue_state_error_count = 0
    queue_overflow_count = 0

    # --------------------------------------------------------
    # 锁
    # --------------------------------------------------------

    stat_lock = _thread.allocate_lock()
    consumed_lock = _thread.allocate_lock()
    print_lock = _thread.allocate_lock()

    # ========================================================
    # 输出
    # ========================================================

    def log(text):
        print_lock.acquire()
        try:
            lib_lsl.send("[测试] {}\n".format(text))
        finally:
            print_lock.release()

    # ========================================================
    # 生成测试数据
    # ========================================================

    def make_item(producer_id, sequence):

        payload = "P{:02d}-S{:06d}-".format(producer_id, sequence)

        payload += "X" * (PAYLOAD_LEN - len(payload))

        return (producer_id, sequence, payload)

    # ========================================================
    # 检查数据
    # ========================================================

    def check_item(item):

        nonlocal corrupt_count

        # 数据必须是 tuple
        if not isinstance(item, tuple):
            corrupt_count += 1
            log("数据错误：不是 tuple：{}".format(item))
            return False

        # 必须有三个元素
        if len(item) != 3:
            corrupt_count += 1
            log("数据错误：tuple 长度错误：{}".format(item))
            return False

        producer_id = item[0]
        sequence = item[1]
        # payload = item[2]

        # 检查范围
        if not (0 <= producer_id < PRODUCER_NUM):
            corrupt_count += 1
            log("数据错误：producer_id={}".format(producer_id))
            return False

        if not (0 <= sequence < ITEMS_PER_PRODUCER):
            corrupt_count += 1
            log("数据错误：sequence={}".format(sequence))
            return False

        # 检查 Payload
        expected = make_item(producer_id, sequence)

        if item != expected:
            corrupt_count += 1
            log("数据损坏：producer={} sequence={}".format(producer_id, sequence))
            return False

        return True

    # ========================================================
    # 生产者
    # ========================================================

    def producer(producer_id):

        nonlocal produce_count
        nonlocal producer_finished

        log("生产者 {} 启动".format(producer_id))

        for sequence in range(ITEMS_PER_PRODUCER):
            item = make_item(producer_id, sequence)

            q.append(item)

            stat_lock.acquire()
            produce_count += 1
            stat_lock.release()

            if PRINT_EVERY_ITEM:
                log("生产 {}：{}".format(producer_id, item))

            if PRODUCER_DELAY_MS:
                time.sleep_ms(PRODUCER_DELAY_MS)

        stat_lock.acquire()
        producer_finished += 1
        stat_lock.release()

        log("生产者 {} 完成".format(producer_id))

    # ========================================================
    # 消费者
    # ========================================================

    def consumer(consumer_id):

        nonlocal consume_count
        nonlocal consumer_finished
        nonlocal duplicate_count

        log("消费者 {} 启动".format(consumer_id))

        while True:
            item = q.popleft()

            # None 是结束标记
            if item is None:
                break

            # 检查数据
            if not check_item(item):
                continue

            producer_id = item[0]
            sequence = item[1]

            key = (producer_id, sequence)

            # ------------------------------------------------
            # 检查重复
            # ------------------------------------------------

            consumed_lock.acquire()

            if key in consumed:
                duplicate_count += 1

                consumed_lock.release()

                log("发现重复数据：{}".format(key))

            else:
                consumed[key] = True

                consumed_lock.release()

            # ------------------------------------------------
            # 消费计数
            # ------------------------------------------------

            stat_lock.acquire()
            consume_count += 1
            stat_lock.release()

            if PRINT_EVERY_ITEM:
                log("消费 {}：{}".format(consumer_id, item))

            if CONSUMER_DELAY_MS:
                time.sleep_ms(CONSUMER_DELAY_MS)

        stat_lock.acquire()
        consumer_finished += 1
        stat_lock.release()

        log("消费者 {} 完成".format(consumer_id))

    # ========================================================
    # Queue 状态监视
    # ========================================================

    def monitor():

        nonlocal queue_state_error_count
        nonlocal queue_overflow_count

        while True:
            # -----------------------------------------------
            # 使用 Queue 自己的锁读取内部状态
            # -----------------------------------------------

            q.lock.acquire()

            length = len(q.data)

            q.lock.release()

            # -----------------------------------------------
            # Queue 不允许超过 max_len
            # -----------------------------------------------

            if length > q.max_len:
                queue_overflow_count += 1

                log("Queue 溢出：len(data)={} max_len={}".format(length, q.max_len))

            # -----------------------------------------------
            # 检查生产者 / 消费者是否完成
            # -----------------------------------------------

            stat_lock.acquire()

            done = (
                producer_finished == PRODUCER_NUM and consumer_finished == CONSUMER_NUM
            )

            stat_lock.release()

            if done:
                break

            time.sleep_ms(10)

    # ========================================================
    # 开始
    # ========================================================

    log("==============================")
    log("开始 Queue 多线程测试")
    log("==============================")

    log("生产者：{} 个".format(PRODUCER_NUM))

    log("消费者：{} 个".format(CONSUMER_NUM))

    log("每个生产者：{} 条".format(ITEMS_PER_PRODUCER))

    log("总数据：{} 条".format(total))

    log("Queue 最大容量：{}".format(QUEUE_MAX_LEN))

    # ========================================================
    # 先启动消费者
    #
    # 此时 Queue 为空。
    # 消费者应该全部阻塞。
    # ========================================================

    log("==============================")
    log("启动消费者")
    log("==============================")

    for i in range(CONSUMER_NUM):
        _thread.start_new_thread(consumer, (i,))

    # 确保消费者进入阻塞
    time.sleep_ms(500)

    q.lock.acquire()

    initial_len = len(q.data)

    q.lock.release()

    log("空队列等待后：len(data)={}".format(initial_len))

    # ========================================================
    # 启动监视线程
    # ========================================================

    _thread.start_new_thread(monitor, ())

    # ========================================================
    # 启动生产者
    # ========================================================

    log("==============================")
    log("启动生产者")
    log("==============================")

    for i in range(PRODUCER_NUM):
        _thread.start_new_thread(producer, (i,))

    # ========================================================
    # 主线程等待生产完成
    # ========================================================

    while True:
        stat_lock.acquire()

        finished = producer_finished
        p = produce_count
        c = consume_count

        stat_lock.release()

        q.lock.acquire()

        q_len = len(q.data)

        q.lock.release()

        log(
            "进度：生产={} / {}，消费={} / {}，队列={}".format(
                p, total, c, total, q_len
            )
        )

        if finished == PRODUCER_NUM:
            break

        time.sleep_ms(1000)

    # ========================================================
    # 所有生产者已经结束
    #
    # 此时加入 CONSUMER_NUM 个结束标记。
    #
    # 它们会排在所有正常数据后面。
    # ========================================================

    log("==============================")
    log("所有生产者完成，加入消费者结束标记")
    log("==============================")

    for _ in range(CONSUMER_NUM):
        q.append(None)

    # ========================================================
    # 等待消费者全部结束
    # ========================================================

    while True:
        stat_lock.acquire()

        finished = consumer_finished
        c = consume_count

        stat_lock.release()

        q.lock.acquire()

        q_len = len(q.data)

        q.lock.release()

        log(
            "等待消费者：消费={} / {}，队列={}，消费者完成={}".format(
                c, total, q_len, finished
            )
        )

        if finished == CONSUMER_NUM:
            break

        time.sleep_ms(1000)

    # ========================================================
    # 最终 Queue 状态
    # ========================================================

    q.lock.acquire()

    final_len = len(q.data)

    q.lock.release()

    # ========================================================
    # 检查丢失数据
    # ========================================================

    missing_count = 0

    for producer_id in range(PRODUCER_NUM):
        for sequence in range(ITEMS_PER_PRODUCER):
            key = (producer_id, sequence)

            consumed_lock.acquire()

            exists = key in consumed

            consumed_lock.release()

            if not exists:
                missing_count += 1

                if missing_count <= 10:
                    log("丢失数据：{}".format(key))

    # ========================================================
    # 最终结果
    # ========================================================

    log("==============================")
    log("最终测试结果")
    log("==============================")

    log("理论数据：{}".format(total))

    log("实际生产：{}".format(produce_count))

    log("实际消费：{}".format(consume_count))

    log("数据损坏：{}".format(corrupt_count))

    log("重复消费：{}".format(duplicate_count))

    log("丢失数据：{}".format(missing_count))

    log("Queue 溢出：{}".format(queue_overflow_count))

    log("Queue 状态错误：{}".format(queue_state_error_count))

    log("最终 len(queue.data)：{}".format(final_len))

    # ========================================================
    # 判断
    # ========================================================

    passed = (
        produce_count == total
        and consume_count == total
        and corrupt_count == 0
        and duplicate_count == 0
        and missing_count == 0
        and queue_state_error_count == 0
        and queue_overflow_count == 0
        and final_len == 0
    )

    log("==============================")

    if passed:
        log("测试通过")
    else:
        log("测试失败")

    log("==============================")

    return passed
