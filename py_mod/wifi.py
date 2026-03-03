import network
import time
import asyncio
import collections
import _thread
import wifilr


class WIFILSL():

    def __init__(self, account={"12345678": "12345678",
                                "CMCC-Ef6Z": "ddtzpts9",
                                "CMCC-vKWf": "7vzpycp6",
                                "CMCC-luoyuan": "A13466179775"},
                 v6公网=False, static=False,
                 ip="192.168.1.189", 子网掩码="255.255.255.0",
                 网关="192.168.1.1", dns_server="192.168.1.1"):

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

        # 没有找到方便点，非侵入的软重启
        # 使用静态ip加快单片机硬重启
        self.account = account
        self.static = static
        self.v6公网 = v6公网
        self.ip = ip
        self.子网掩码 = 子网掩码
        self.网关 = 网关
        self.dns_server = dns_server

        self.单个wifi尝试时间 = 30
        self.检查间隔 = 30

        self.static_ip = (ip, 子网掩码, 网关, dns_server)

        if self.static:
            self.wlan.ifconfig(self.static_ip)

    @staticmethod
    def get_v6_str():
        return wifilr.get_ipv6_addr()

    # 多线程 wifi
    def conn_thr(self, ssid=None, passwd=None):
        _thread.start_new_thread(self._conn_thr, (ssid, passwd))

    def _conn_thr(self, ssid=None, passwd=None):
        while True:
            self.conn_one(ssid, passwd)
            time.sleep(self.检查间隔)

    def conn_one(self, ssid=None, passwd=None):
        if self.wlan.isconnected():
            self._get_v6()

        while not self.wlan.isconnected():
            acc = self._获取需要连接的wifi(ssid, passwd)

            # 连接wifi
            for sid in acc:
                self.wlan.disconnect()
                self.wlan.connect(sid, acc[sid])
                s = time.time()
                while (time.time() - s) <= self.单个wifi尝试时间:
                    if self.wlan.isconnected():
                        self._get_v6()
                        # webrepl.start(password="1234")
                        return
                    time.sleep(0.1)
            time.sleep(1)

    def _get_v6(self):
        if not self.v6公网:
            return

        # 协商v6地址
        wifilr.get_ipv6()

        # 3大运营商v6都用2开头，先简单处理一下
        while True:
            ret = wifilr.get_ipv6_addr()
            for v6 in ret:
                if v6[0:1] == "2":
                    return
            time.sleep(0.3)

    # async wifi
    async def conn_async(self, ssid=None, passwd=None):
        while True:
            await self.conn_one_async(ssid, passwd)
            await asyncio.sleep(self.检查间隔)

    async def _conn_one_async(self, ssid=None, passwd=None):
        if self.wlan.isconnected():
            await self._get_v6_async()

        while not self.wlan.isconnected():
            acc = self._获取需要连接的wifi(ssid, passwd)

            # 连接wifi
            for sid in acc:
                self.wlan.disconnect()
                self.wlan.connect(sid, acc[sid])
                s = time.time()
                while (time.time() - s) <= self.单个wifi尝试时间:
                    if self.wlan.isconnected():
                        # webrepl.start(password="1234")
                        await self.get_v6_async()
                        return
                    await asyncio.sleep(0.1)

            await asyncio.sleep(1)

    async def _get_v6_async(self):
        if not self.v6公网:
            return

        # 协商v6地址
        wifilr.get_ipv6()

        # 3大运营商v6都用2开头，先简单处理一下
        while True:
            ret = wifilr.get_ipv6_addr()
            for v6 in ret:
                if v6[0:1] == "2":
                    return
            await asyncio.sleep(0.3)

    # 如果连接时提供了account单独处理
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
        周围信号 = sorted(self.wlan.scan(), key=lambda x: x[3], reverse=True)

        # 本地wifi账号 和 周围wifi账号的交集
        for 单个周围信号 in 周围信号:
            ssid = 单个周围信号[0].decode("utf-8")
            if ssid in self.account:
                ret_acc[ssid] = self.account[ssid]

        return ret_acc
