import network
import time
import asyncio
import collections
import _thread

try:
    import wifilr
except:  # noqa: E722
    pass


# 有多次初始化需求
# 多次初始化，返回第一次的对象，只修改v6公网参数
class WIFI:
    _单例对象 = None
    _is_init = False
    _is_task_run = False

    def __new__(cls, *args, **kwargs):
        # 如果实例不存在，则创建一个
        if cls._单例对象 is None:
            cls._单例对象 = super(WIFI, cls).__new__(cls)
        return cls._单例对象

    def __init__(
        self,
        account={
            "12345678": "12345678",
            "CMCC-Ef6Z": "ddtzpts9",
            "CMCC-vKWf": "7vzpycp6",
            "CMCC-luoyuan": "A13466179775",
        },
        v6公网=False,
        static=False,
        ip="192.168.1.189",
        子网掩码="255.255.255.0",
        网关="192.168.1.1",
        dns_server="192.168.1.1",
    ):

        # 如果已经初始化过了
        if WIFI._is_init:
            self.v6公网 = v6公网
            return

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.disconnect()

        # 没有找到方便点，非侵入的软重启
        # 使用静态ip加快单片机硬重启
        self.account = account
        self.static = static
        self.v6公网 = v6公网
        self.ip = ip
        self.子网掩码 = 子网掩码
        self.网关 = 网关
        self.dns_server = dns_server

        self.单个wifi尝试时间ms = 30_000
        self.检查间隔ms = 1_000
        self.单次v6协商等待时间ms = 60_000

        self.static_ip = (ip, 子网掩码, 网关, dns_server)

        if self.static:
            self.wlan.ifconfig(self.static_ip)

        WIFI._is_init = True

    def _获取需要连接的wifi(self, ssid=None, passwd=None):
        if ssid is None:
            acc = self._获取交集()
        elif passwd is None:
            acc = {ssid: self.account[ssid]}
        else:
            acc = {ssid: passwd}

        return acc

    # 本地wifi账号 和 周围wifi账号的交集，信号质量排序
    def _获取交集(self):

        # 排序后信息
        ret_acc = collections.OrderedDict()

        # 获取周围信号，然后按照信号强度排序
        周围信号 = sorted(self.wlan.scan(), key=lambda x: x[3], reverse=True)  # type: ignore

        # 本地wifi账号 和 周围wifi账号的交集
        for 单个周围信号 in 周围信号:
            try:
                ssid = 单个周围信号[0].decode("utf-8")
            except:  # noqa: E722
                continue
            if ssid in self.account:
                ret_acc[ssid] = self.account[ssid]  # type: ignore

        return ret_acc

    # 获取v6字符串

    @staticmethod
    def get_v6_str():
        return wifilr.get_ipv6_addr()

    # 阻塞到获取v6公网字符串成功
    @staticmethod
    def get_v6公网_str_阻塞(间隔ms=30, 超时ms=120_000):
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < 超时ms:
            v6s = wifilr.get_ipv6_addr()
            for v6 in v6s:
                if WIFI.is_公网_v6(v6):
                    return v6s
            time.sleep_ms(间隔ms)
        raise OSError("超时,没有获取到公网ipv6")

    # 我遇到的ipv6公网地址都是是2开头
    # 这是gpt实现的函数，我没有查证ipv6分配规则
    @staticmethod
    def is_公网_v6(addr):
        if not addr:
            return False

        addr = addr.lower()

        # 基本格式检查
        if ":" not in addr:
            return False

        # 排除特殊地址
        if addr == "::" or addr == "::1":
            return False

        if addr.startswith("fe80"):
            return False

        if addr.startswith("fc") or addr.startswith("fd"):
            return False

        # 公网 ipv6 范围 2000::/3
        if addr[0] in ("2", "3"):
            return True

        return False

    # 线程中维护wifi连接
    def conn_thr(self, ssid=None, passwd=None):
        if WIFI._is_task_run:
            return
        else:
            WIFI._is_task_run = True
        _thread.start_new_thread(self._conn_thr, (ssid, passwd))

    # 线程中维护wifi连接
    def _conn_thr(self, ssid=None, passwd=None):
        while True:
            self.conn_one(ssid, passwd)
            time.sleep_ms(self.检查间隔ms)

    async def conn_async(self, ssid=None, passwd=None):
        # 弄个假的，避免任务死亡提示
        if WIFI._is_task_run:
            while True:
                await asyncio.sleep_ms(100_000_000)
        else:
            WIFI._is_task_run = True

        while True:
            await self.conn_one_async(ssid, passwd)
            await asyncio.sleep_ms(self.检查间隔ms)

    # 连接一次WiFi
    def conn_one(self, ssid=None, passwd=None):
        # 协商v6公网
        if self.wlan.isconnected():
            self._get_v6()

        while not self.wlan.isconnected():
            acc = self._获取需要连接的wifi(ssid, passwd)
            # 连接wifi
            for sid in acc:
                self.wlan.disconnect()
                self.wlan.connect(sid, acc[sid])  # type: ignore
                t0 = time.ticks_ms()
                while time.ticks_diff(time.ticks_ms(), t0) < self.单个wifi尝试时间ms:
                    if self.wlan.isconnected():
                        return
                    time.sleep_ms(30)
            time.sleep_ms(1000)

    # 协商公网V6地址
    def _get_v6(self):

        # 不需要V6地址
        if not self.v6公网:
            return

        # 已经有V6地址了，避免多次协商
        ret = wifilr.get_ipv6_addr()
        for v6 in ret:
            if WIFI.is_公网_v6(v6):
                return

        # 协商v6地址
        wifilr.get_ipv6()

        # 协商后等待
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < self.单次v6协商等待时间ms:
            ret = wifilr.get_ipv6_addr()
            for v6 in ret:
                if WIFI.is_公网_v6(v6):
                    return  # 成功获取到公网地址
            time.sleep_ms(30)

    """
        携程版本
            1、别忘记复制粘贴一份conn_one和get_v6函数
            2、并且修改get_v6()函数名字
    """

    async def conn_one_async(self, ssid=None, passwd=None):
        # 协商v6公网
        if self.wlan.isconnected():
            await self._get_v6_async()

        while not self.wlan.isconnected():
            acc = self._获取需要连接的wifi(ssid, passwd)
            # 连接wifi
            for sid in acc:
                self.wlan.disconnect()
                self.wlan.connect(sid, acc[sid]) # type: ignore
                t0 = time.ticks_ms()
                while time.ticks_diff(time.ticks_ms(), t0) < self.单个wifi尝试时间ms:
                    if self.wlan.isconnected():
                        return
                    await asyncio.sleep_ms(50)
            await asyncio.sleep_ms(1000)

    async def _get_v6_async(self):

        # 不需要V6地址
        if not self.v6公网:
            return

        # 已经有V6地址了，避免多次协商
        ret = wifilr.get_ipv6_addr()
        for v6 in ret:
            if WIFI.is_公网_v6(v6):
                return

        # 协商v6地址
        wifilr.get_ipv6()

        # 协商后等待
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < self.单次v6协商等待时间ms:
            ret = wifilr.get_ipv6_addr()
            for v6 in ret:
                if WIFI.is_公网_v6(v6):
                    return  # 成功获取到公网地址
            await asyncio.sleep_ms(30)


# 检查问题
# 忽略线程安全
# 忽略await asyncio.sleep_ms(100_000_000)
# 忽略单例只修改v6公网
# 忽略中文标识符
