import socket
import _thread


class _udp_log:
    def __init__(self):
        self.udp_print = False
        self.ip = None
        self.port = 50002
        self.uart_print = False
        self._cnt = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.war = "warning_lr "
        self.err = "error_lr "
        self.ok = "ok_lr "
        self.lock = _thread.allocate_lock()
        self._err_num = 0

    # 配置日志对象,来启用打印
    def set_config(self, ip=None, port=None, udp=True, uart_print=False):
        with self.lock:
            if ip is not None:
                self.ip = ip
            if port is not None:
                self.port = port

            self.udp_print = udp
            self.uart_print = uart_print

    # 所有外部访问函数统一调用此函数
    def send(self, *args, hed=""):

        if self.uart_print:
            print(*args)

        try:
            if self.udp_print:
                msg = " ".join([str(x) for x in args])
                with self.lock:
                    self._cnt += 1
                    self.sock.sendto(
                        f"{hed}{self._err_num} {self._cnt} {msg}".encode(),
                        (self.ip, self.port),
                    )
        except:
            with self.lock:
                self._err_num += 1

    def send_war(self, *args):
        self.send(*args, hed=self.war)

    def send_err(self, *args):
        self.send(*args, hed=self.err)

    def send_ok(self, *args):
        self.send(*args, hed=self.ok)


# 实例化对象
_ul = _udp_log()

# 外部接口
set_config = _ul.set_config
send = _ul.send
send_war = _ul.send_war
send_err = _ul.send_err
send_ok = _ul.send_ok
