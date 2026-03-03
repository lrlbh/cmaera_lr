import _thread

import socket
import binascii
import hashlib
import time


class WsScoket():
    def __init__(self, socket: socket.socket):
        self.socket = socket

    def send(self, data):
        # 数据长度
        data_len = len(data)

        # 构建头
        frame = bytearray()

        # ===== 第一个字节 =====
        # FIN=1, opcode=1 (text)
        if isinstance(data, str):
            data = data.encode()
            frame.append(0x81)
        else:
            frame.append(0x82)

        # ===== 第二个字节 + 扩展长度 =====
        if data_len <= 125:
            frame.append(data_len)
        elif data_len <= 0xFFFF:
            frame.append(126)
            frame.extend(data_len.to_bytes(2, 'big'))

        else:
            frame.append(127)
            frame.extend(data_len.to_bytes(8, 'big'))

        self.socket.sendall(frame)
        self.socket.sendall(data)


class Server():
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

        # 浏览器似乎会一直重复发起连接
        # 不过只有用户知道的连接会携带不一样的key
        self.key = []

        # 通过get获取处理好的连接
        # self.client = []
        self.http = []
        self.ws = []

    # 在线程中，持续获取连接
    def _work(self):
        while True:
            if len(self.ws) + len(self.http) > 3:
                time.sleep(0.3)
                continue

            conn, addr = self.accept_all()

            if isinstance(conn, WsScoket):
                self.ws.append((conn, addr))
            else:
                self.http.append((conn, addr))

    # 启动自动获取连接线程

    def run_thr(self):
        _thread.start_new_thread(self._work, ())
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
                if len(self.buf) >= 4 and self.buf[-4:] == b'\r\n\r\n':
                    self.conn.settimeout(None)
                return
            except (OSError, Exception) as e:
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

                    key = self.buf[index+19:index+19+24] + \
                        b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                    if len(self.key) > 1000:
                        self.key = []
                    if key in self.key:
                        raise Exception(f"浏览器连接，不处理{time.time()}")
                    self.key.append(key)
                    sha1 = hashlib.sha1(key)
                    base64 = binascii.b2a_base64(
                        sha1.digest()).decode().strip()

                    response = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {base64}\r\n\r\n"
                    )
                    self.conn.sendall(response.encode('utf-8'))

                    return WsScoket(self.conn), self.addr

                # 没有确认是否是http
                return self.conn, self.addr
            except Exception as E:
                print(E)
                self.conn.close()

    # 手动获取一个ws连接,丢掉其他连接
    def accept_ws(self):
        while True:
            conn, addr = self.accept_all()
            if isinstance(conn, WsScoket):
                return conn, addr
            conn.close()

    # 手动获取一个http连接,丢掉其他连接
    def accept_http(self):
        while True:
            conn, addr = self.accept_all()
            if not isinstance(conn, WsScoket):
                return conn, addr
            conn.close()
