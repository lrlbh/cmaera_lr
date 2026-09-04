import errno
import machine
import socket
import binascii
import hashlib
import time

import lib_lsl
import lib_lsl.tl
import tl_lr


# 基于阻塞的WS套接字
class WsSocket:
    def __init__(self, socket_in: socket.socket, max_msg_len=6 * 1024 * 1024):
        self.socket: socket.socket = socket_in
        self.timeout = None
        self.max_msg_len = max_msg_len
        self.head_buf = bytearray(8)
        self.is_close = False

    # 转接 socket 中的方法
    def __getattr__(self, name):
        return getattr(self.socket, name)

    # mpy判断是否close不方便,覆盖close
    def close(self):
        self.is_close = True
        self.socket.close()

    @staticmethod
    def socket_close(func):
        # 是否需要可以关闭日志打印？

        func_name = func.__name__

        def wrapper(self, *args, **kwargs):

            # 无法获取到参数名称，也无法确定addr长度
            # 所以假设它第2个参数，同时为元组
            if len(args) >= 2 and isinstance(args[1], tuple):
                addr = args[1]
            else:
                addr = "addr参数无法识别! 需要是第二个参数同时为元组"

            try:
                try:
                    # 执行函数
                    ret = func(self, *args, **kwargs)
                    lib_lsl.send(f"{func_name} --> {addr} --> 正常退出函数")
                    return ret  # 放心finally会在返回前被执行的

                except OSError as e:
                    lib_lsl.send(
                        f"{func_name} --> {addr} --> 退出: {lib_lsl.tl.get_完整错误信息(e)}"
                    )

                finally:
                    self.close()

            except Exception as e:
                lib_lsl.send_err(
                    f"{func_name} --> {addr} --> 退出: {lib_lsl.tl.get_完整错误信息(e)}"
                )

        return wrapper

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

        # str 编码在后计算len
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
        frame = bytearray()

        if isinstance(data, str):
            data = data.encode()
            frame.append(0x81)
        else:
            frame.append(0x82)

        data_len = len(data)

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

    def read_ws(self, buf=None):
        """
        字符串消息
            总是返回新的字符串
            但buf可以当作缓存加速
            buf长度不够行为也和bin一样
        bin消息
            buf != nil
                buf长度足够
                    返回memoryview
                buf长度不够
                    扩展用户buf?
                    返回新的bytearray()?
                    抛出错误显式处理？----暂时定此种处理方式
            buf == nil
                返回新的bytearray()
        --------------------------------------------------
        是否需要恢复错误？大部分错误恢复很简单
        重连一下完事了，吃饱了没事干,在外面判断一堆错误
        抛出,及时记录,修复,当前场景下明显更方便
        """

        # ws保证单条任何类型消息至少有2字节
        lib_lsl.tl.readinto_exact(self.socket, self.head_buf, 2)

        # fin
        if (self.head_buf[0] & 0x80) == 0:
            # 在这里抛出情况下，此错误上下文错乱，不要恢复
            raise Exception("WS没实现消息分片")

        if self.head_buf[0] & 0x70:
            raise Exception("WS非标协议 RSV位非0")

        #  Opcode
        opcode = self.head_buf[0] & 0x0F

        # pong和 close都应该被当作一条完整的消息处理
        # ----------------------------------------------
        # 我查到的标准流程是  收到close --> 回复close --> server主动.tcp.close
        # 瞎几把扯啊，不可能啊，应该需要发送close的主动调用tcp.close才对吧
        # 即时一定要服务器先关闭，也应该这样才对
        # 1、close --> 回复close -->服务器先半关闭-->等待客服端也半关闭然后--> server.tcp.close
        # 2、查下资料tcp必须保证，close的数据必须在缓冲区清空后才会发送
        # ----------------------------------------------
        # 如果要回复的话必然要加锁，并且禁止用户访问tcp套接字发送数据了，有时间再写
        if opcode == 0x8:
            # 直接用此种方式，对方的close事件应该会被异化为ERROR事件
            self.close()
            raise Exception("收到ws_close,直接断开了TCP")

        # 不处理其他消息
        if opcode != 0x1 and opcode != 0x2:
            # 在这里抛出情况下，此错误上下文错乱，不要恢复
            raise Exception(
                f"WS只支持str、bytes、colose(伪)消息类型! opcode: {opcode:#x}"
            )

        # 解析消息类型
        is_str = opcode == 0x1

        # 解析是否有掩码,允许客服端发送无掩码数据
        is_masked = (self.head_buf[1] & 0x80) != 0

        # 解析消息长度
        msg_len = self.head_buf[1] & 0x7F
        # 扩展长度下,长度不应该小于125(?),没有校验
        if msg_len == 126:
            lib_lsl.tl.readinto_exact(self.socket, self.head_buf, 2)
            msg_len = int.from_bytes(self.head_buf[0:2], "big")
        elif msg_len == 127:
            lib_lsl.tl.readinto_exact(self.socket, self.head_buf, 8)
            if self.head_buf[0] & 0x80:
                # 在这里抛出情况下，此错误上下文错乱，不要恢复
                raise Exception("非法WS消息长度,64bit需要最高位为0")
            msg_len = int.from_bytes(self.head_buf, "big")

        if msg_len > self.max_msg_len:
            # 在这里抛出情况下，此错误上下文错乱，不要恢复
            raise Exception("ws消息长度,大于允许长度")

        # 读取掩码 Key
        if is_masked:
            mask_key = lib_lsl.tl.read_exact(self.socket, 4)

        # 读取数据
        if buf is None:
            msg = lib_lsl.tl.read_exact(self.socket, msg_len)
        elif len(buf) < msg_len:
            # 在这里抛出情况下，此错误上下文错乱，不要恢复
            raise Exception("ws长度大于传入buf")
        else:
            lib_lsl.tl.readinto_exact(self.socket, buf, msg_len)
            msg = memoryview(buf)[:msg_len]

        # 如果有掩码，进行异或解码
        if is_masked:  # and is_str:
            # s = time.ticks_us()
            # tl_lr.ws_mask_decode(msg, mask_key)
            tl_lr.ws_mask_decode_2(msg, mask_key)
            # e = time.ticks_diff(time.ticks_us(), s)
            # lib_lsl.send(f"耗时: {e / 1000} ms")

        # 转换为对应的数据类型返回
        if is_str:
            try:
                # return msg.decode()
                return str(msg, "utf8")
            except UnicodeError:
                raise Exception("WS收到字符串消息,但解码为utf-8失败")
        else:
            return msg

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


# 没有提供async版本，因为协程版本tcp速率显著更慢，可能协程API实现有问题
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
                if e.errno != 23:  # 原因非套接字上限,继续抛出
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
        lib_lsl.Thread.create_thread(self._work, (套接字上限,))
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
            except:
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
            except Exception:
                # print(e)
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
