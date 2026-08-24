import _thread
import errno
import machine
import socket
import binascii
import hashlib
import time

import lib_lsl


class WsSocket:
    def __init__(self, socket: socket.socket):
        self.socket = socket
        self.timeout = None

    # 转接 socket 中的方法
    def __getattr__(self, name):
        return getattr(self.socket, name)

    def send_ws(self, data):

        # 构建头
        frame = bytearray()

        # ===== 第一个字节 =====
        # FIN=1, opcode=1 (text)
        if isinstance(data, str):
            data = data.encode()
            frame.append(0x81)
        else:
            frame.append(0x82)

        data_len = len(data)

        # ===== 第二个字节 + 扩展长度 =====
        if data_len <= 125:
            frame.append(data_len)
        elif data_len <= 0xFFFF:
            frame.append(126)
            frame.extend(data_len.to_bytes(2, "big"))

        else:
            frame.append(127)
            frame.extend(data_len.to_bytes(8, "big"))

        # 据说和python不同
        # mpy的sendall在非阻塞下的行为是 undefined。
        # 懒得处理,mpy推荐用write,阻塞发完,非阻塞自己保证
        self.sendall(frame)
        self.sendall(data)

    # 返回一个编码后可以直接发送的bytes
    @staticmethod
    def get_msg(data):
        if isinstance(data, str):
            data = data.encode()
            opcode = 0x81
        else:
            opcode = 0x82

        data_len = len(data)

        frame = bytearray()
        frame.append(opcode)

        if data_len <= 125:
            frame.append(data_len)
        elif data_len <= 0xFFFF:
            frame.append(126)
            frame.extend(data_len.to_bytes(2, "big"))
        else:
            frame.append(127)
            frame.extend(data_len.to_bytes(8, "big"))

        frame.extend(data)

        return bytes(frame)

    #  None(阻塞), 0(非阻塞), 或浮点数(秒)
    def settimeout_lr(self, timeout):
        self.timeout = timeout
        self.settimeout(timeout)

    def read_ws_temp(self):
        """
        图方便的非阻塞读取函数

        没数据返回长度为0的数据 ""
        有数据返回str或者bytes

        没有处理错误情况的现场
        如果报错,大概率上下文都错乱了
        所以报错,外部就关掉这个套接字
        """

        # 临时设置为非阻塞
        self.setblocking(False)

        try:
            b1 = self.recv(1)[0]
        except OSError as e:
            # if e.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
            if e.args[0] == errno.EAGAIN:
                return ""
            else:
                raise

        b2 = self.recv(1)[0]

        # 要求 1 校验：检查 FIN 位（最高位），如果为 0 代表是分片帧
        fin = (b1 & 0x80) != 0
        if not fin:
            raise Exception("没实现消息分片")

        # 要求 2 校验：检查 Opcode（低4位）
        opcode = b1 & 0x0F
        if opcode != 0x1 and opcode != 0x2:
            raise Exception("只支持str和bytes消息类型")

        is_text = opcode == 0x1

        is_masked = (b2 & 0x80) != 0
        payload_len = b2 & 0x7F

        # 解析扩展长度
        if payload_len == 126:
            ext = self.recv(2)
            if not ext or len(ext) < 2:
                raise Exception("读取消息长度失败,2字节扩展情况")
            payload_len = int.from_bytes(ext, "big")
        elif payload_len == 127:
            ext = self.recv(8)
            if not ext or len(ext) < 8:
                raise Exception("读取消息长度失败,8字节扩展情况")
            payload_len = int.from_bytes(ext, "big")

        # 读取掩码 Key
        mask_key = None
        if is_masked:
            mask_key = self.recv(4)
            if not mask_key or len(mask_key) < 4:
                raise Exception("读取掩码失败")

        # 循环读取完整的 Payload 数据
        data = bytearray()
        while len(data) < payload_len:
            chunk = self.recv(payload_len - len(data))
            if not chunk:
                break
            data.extend(chunk)

        # 恢复套接字阻塞状态
        self.settimeout_lr(self.timeout)

        if len(data) < payload_len:
            raise Exception("没有读取到完整消息")

        # 如果有掩码，进行异或解码
        if is_masked:
            for i in range(payload_len):
                data[i] ^= mask_key[i % 4]

        # 转换为对应的数据类型返回
        if is_text:
            try:
                return bytes(data).decode("utf-8")
            except UnicodeError:
                raise Exception("字符串消息,但解码为utf-8失败")
        else:
            return bytes(data)


class t套接字上限行为:
    重启 = 0
    等待 = 1


class Server:
    def __init__(self, ip, port, listen):
        if ":" in ip:
            ipv = socket.AF_INET6
        else:
            ipv = socket.AF_INET

        self.s = socket.socket(ipv, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((ip, port))
        self.s.listen(listen)

        self.conn = None
        self.addr = None
        self.buf = bytearray()

        # 浏览器有时似乎会一直重复发起连接
        # 不过只有用户知道的连接会携带不一样的key
        self.key = []

        # 通过get获取处理好的连接
        # self.client = []
        self.http = []
        self.ws = []

    # 在线程中，持续获取连接
    def _work(self, 套接字上限):
        while True:
            if len(self.ws) + len(self.http) >= 2:
                time.sleep_ms(300)
                continue
            try:
                conn, addr = self.accept_all()
            except OSError as e:
                if e.errno != 23:
                    raise
                if 套接字上限 == t套接字上限行为.重启:
                    machine.reset()
                elif 套接字上限 == t套接字上限行为.等待:
                    time.sleep_ms(300)
                    continue
                else:
                    raise Exception("未定义的套装字上限行为")

            if isinstance(conn, WsSocket):
                self.ws.append((conn, addr))
            else:
                self.http.append((conn, addr))

    # 启动自动获取连接线程
    # rst,没有套接字资源时是否重启
    def run_thr(self, 套接字上限=t套接字上限行为.等待):
        _thread.start_new_thread(self._work, (套接字上限,))
        return self

    # 处理 ws和http_get 请求头
    def _accept(self):
        while True:
            # 获取连接
            self.conn, self.addr = self.s.accept()

            # 避免读取超时
            self.conn.settimeout(3)

            # 接收握手请求，超时关闭
            try:
                # 意外读不够，直接关了算了，暂不处理
                self.buf = self.conn.recv(1024)
                if len(self.buf) >= 4 and self.buf[-4:] == b"\r\n\r\n":
                    self.conn.settimeout(None)
                return
            except:  # noqa: E722
                pass

            # 不处理的连接关闭
            self.conn.close()

    # 手动获取一个_accept支持的任意连接
    def accept_all(self):
        # 必须阻塞到有一个连接
        while True:
            self._accept()
            # 万一bug,释放连接
            try:
                # print(self.buf.decode())
                if b"Upgrade: websocket" in self.buf:
                    index = self.buf.find(b"Sec-WebSocket-Key: ")
                    if index == -1:
                        raise Exception("ws 没有 key")

                    key = (
                        self.buf[index + 19 : index + 19 + 24]
                        + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                    )
                    if len(self.key) > 1000:
                        self.key = []
                    if key in self.key:
                        raise Exception(f"浏览器连接，不处理{time.time()}")
                    self.key.append(key)
                    sha1 = hashlib.sha1(key)
                    base64 = binascii.b2a_base64(sha1.digest()).decode().strip()

                    response = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {base64}\r\n\r\n"
                    )
                    self.conn.sendall(response.encode("utf-8"))

                    return WsSocket(self.conn), self.addr  # type: ignore

                # 没有确认是否是http
                return self.conn, self.addr
            except Exception as e:  
                # print(e)
                lib_lsl.send(e)
                self.conn.close()

    # 手动获取一个ws连接,丢掉其他连接
    def accept_ws(self):
        while True:
            conn, addr = self.accept_all()
            if isinstance(conn, WsSocket):
                return conn, addr
            conn.close()

    # 手动获取一个http连接,丢掉其他连接
    def accept_http(self):
        while True:
            conn, addr = self.accept_all()
            if not isinstance(conn, WsSocket):
                return conn, addr
            conn.close()  # type: ignore
