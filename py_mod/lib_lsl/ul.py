import socket


class _udp_log:
    def __init__(self):

        # try:
        #     with open("/no_delete/ip.txt", "r") as f:
        #         ip = f.read().strip()
        # except:
        #     ip = None

        # # 文件存在才允许发送
        # self.ok = False
        # if tl.file_exists("/boot_run.py") or tl.file_exists("/Alr/boot_run.py"):
        #     self.ok = True

        self.udp_print = False
        self.ip = None
        self.port = 9001
        self.print = False
        self._cnt = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.war = "warning_lr "
        self.err = "error_lr "
        self.ok = "ok_lr "

    def set_addr(self, ip=None, port=None):
        if ip is not None:
            self.ip = ip
        if port is not None:
            self.port = port

    def _send(self, *args, hed=""):

        if self.print:
            print(*args)

        if self.udp_print:
            self._cnt += 1
            try:
                msg = " ".join(map(str, args))
                self.sock.sendto(
                    "{}{} {}".format(hed, self._cnt, msg).encode(), (self.ip, self.port)
                )
            except:  # noqa: E722
                pass

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


_ul = _udp_log()


set_addr = _ul.set_addr
send = _ul.send
send_war = _ul.send_war
send_err = _ul.send_err
send_ok = _ul.send_ok
send_diy = _ul.send_diy
