import socket


class _udp_log:
    def __init__(self):
        self.udp_print = False
        self.ip = None
        self.port = 50002
        self.print = False
        self._cnt = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.war = "warning_lr "
        self.err = "error_lr "
        self.ok = "ok_lr "

    # 配置日志对象,来启用打印
    def set_config(self, ip=None, port=None, udp=True, print_lr=False):
        if ip is not None:
            self.ip = ip
        if port is not None:
            self.port = port

        self.udp_print = udp
        self.print = print_lr

    # 所有外部访问函数统一调用此函数
    def _send(self, *args, hed=""):

        if self.print:
            print(*args)

        if self.udp_print:
            self._cnt += 1
            try:
                msg = " ".join(map(str, args))
                self.sock.sendto(
                    f"{hed}{self._cnt} {msg}".encode(),
                    (self.ip, self.port),
                )
            except:
                pass

    # 不同函数加个不同的头,方便UI显示颜色
    def send(self, *args):
        self._send(*args)

    def send_diy(self, *args, hed=""):
        self._send(*args, hed=hed)

    def send_war(self, *args):
        self._send(*args, hed=self.war)

    def send_err(self, *args):
        self._send(*args, hed=self.err)

    def send_ok(self, *args):
        self._send(*args, hed=self.ok)


# 实例化对象
_ul = _udp_log()

# 外部接口
set_config = _ul.set_config
send = _ul.send
send_war = _ul.send_war
send_err = _ul.send_err
send_ok = _ul.send_ok
send_diy = _ul.send_diy
