import json
import time
import lib_lsl
from lib_lsl import WIFI
import lib_lsl.tl
import ws_lsl
import socket


# html = html.encode()

with open("1.html", "rb") as f:
    html = f.read()


html = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: text/html; charset=utf-8\r\n"
    b"Content-Length: " + str(len(html)).encode() + b"\r\n"
    b"Connection: close\r\n"
    b"\r\n" + html
)

# lib_lsl.set_addr("192.168.1.8")
# lib_lsl._ul.udp_print = True


wifi = WIFI(static=True)
wifi.conn_one("CMCC-Ef6Z")
lib_lsl.send(wifi.wlan.isconnected())

lib_lsl.send(wifi.wlan.ifconfig()[0])

ws = ws_lsl.Server("0.0.0.0", 8000, 0).run_thr()


conn: ws_lsl.WsSocket = None
while True:
    # http请求 回复网页
    while len(ws.http):
        lib_lsl.send("http连接处理 -> ")
        client, _ = ws.http.pop(0)
        try:
            client.settimeout(0.5)
            client.sendall(html)
            lib_lsl.send("成功!")
        except Exception as e:
            lib_lsl.send(f"失败: \n{e}")

        client.close()

    # ws请求 断开上一个连接,只向最新的连接发送
    while len(ws.ws):
        lib_lsl.send(f"新的ws请求到达{time.time()}")
        if conn is not None:
            conn.close()
        conn, _ = ws.ws.pop(0)
        conn.settimeout(0.66)  # 潜在 BUG send_ws时sendall未定义行为

    # 没客服端
    if conn is None:
        continue

    # 读
    try:
        # 非阻塞读取一条消息
        data = conn.read_ws_temp()

        # 有消息处理
        if len(data):
            # 可以统一为str
            if isinstance(data, bytes):
                data = data.decode()

            # 客户端要求每次消息长度
            msg_len = int(data[1:])

            # 非阻塞套接字,方便发送
            conn.settimeout_lr(None)

            if data[0] == "s":
                # ws会导致速度比tcp慢，但浏览器能不能实时获取不完整的ws消息?
                msg = conn.get_msg(b"x" * msg_len)  # 不可以出现 E [,包括中文里面
                view = memoryview(msg)
                while True:  # 直接死循环完事了,要停止浏览器关闭套接字
                    conn.write(view)
                    # conn.sendall(view)

            elif data[0] == "r":
                buf = bytearray(20480)
                while True:  # 直接死循环完事了,要停止浏览器关闭套接字
                    if conn.readinto(buf) == 0:
                        raise Exception("连接已关闭")

            else:  # 错误信息抛出错误,启用套接字方便
                lib_lsl.send(f"收到未知协议: {data}")
                raise Exception(f"收到未知协议: {data}")

    except Exception as e:
        lib_lsl.send(f"接收消息处失败: {lib_lsl.tl.get_完整错误信息(e)}")
        conn = None
        continue

    # 写
    data = None
    try:
        lib_lsl.send("扫描WIFI信号。。。")
        # 获取周围wifi数据
        raw_networks = wifi.wlan.scan()

        # 解析为json数据
        clean_networks = []
        for net in raw_networks:
            ssid, bssid, channel, rssi, authmode, hidden = net

            try:
                wifi_name = ssid.decode("utf-8") if ssid else "空wifi名称"
            except UnicodeDecodeError:
                wifi_name = "非UTF-8 WIFI名称"

            clean_networks.append(
                {
                    "name": wifi_name,
                    "mac": bssid.hex(),
                    "channel": channel,  # 信道
                    "rssi": rssi,  # 信号强度
                    "authmode": authmode,  # 加密认证模式
                    "hidden": hidden,  # 是否隐藏
                }
            )

        # 转为byte
        data = json.dumps(clean_networks).encode()
    except Exception as e:
        data = f"ERROR:{lib_lsl.tl.get_完整错误信息(e)}".encode()

    try:
        conn.send_ws(data)
    except Exception as e:
        lib_lsl.send(lib_lsl.tl.get_完整错误信息(e))
        conn = None

"""
    给我实现一个配套的html客服端,需要3个功能
    - 单片机发
        . 这部分名字保持单片机发
        . 带宽计算要求合理,接收时判断超过N秒就已实际时间戳来计算,不要用定时器然后固定除N秒
        . 实时带宽用图形显示曲线
        . 需要可以输入每条消息大小与单片机协商

    - 单片机收
        . 这部分名字保持单片机收
        . 带宽计算要求合理
        . 实时带宽用图形显示

    - wifi信号显示
        这是默认开启的,但进入测速后就没价值了,因为单片机不会发送数据了
        显示完整数据到一行
        信号强度需要图形显示曲线
        用wifi名和mac作为ID,如果下次多出信号就实时添加,如果缺少信号就用最差信号替代


    其他
        . 带宽单位用Mbps
        . 总数据量用单位(?)iB,比如MiB
        . 使用简单的浏览器刷新来退出测速,所以刷新时需要强制断开ws连接,让单片机解除死循环
"""
