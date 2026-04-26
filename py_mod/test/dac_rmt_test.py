import time

import socket

from dac_lsl import RMT
import lib_lsl

from lib_lsl import WIFI
import rmt_lr

WIFI().conn_one()


# def rmt_sync_client():
#     # 初始化 RMT
#     driver = RMT(gpio=48, 缓冲区长度=8096, 缓冲区数量=3)

#     server_ip = "192.168.1.5"
#     server_port = 30000

#     while True:
#         try:
#             lib_lsl.send(f"尝试连接到 {server_ip}...")
#             # 创建标准 TCP Socket
#             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             s.connect((server_ip, server_port))
#             lib_lsl.send("连接成功！")

#             while True:
#                 mem_buf = driver.get_mem()
#                 try:
#                     bytes_received = s.readinto(mem_buf)
#                     if bytes_received == 0:
#                         lib_lsl.send("服务端关闭连接")
#                         break
#                     driver.return_mem(mem_buf, data_len=bytes_received)

#                 except OSError as e:
#                     lib_lsl.send(f"读取数据失败: {e}")
#                     break

#             s.close()

#         except Exception as e:
#             lib_lsl.send(f"连接错误: {e}")
#             time.sleep(1)  # 失败后等待 5 秒重试


# rmt_sync_client()


def rmt_sync_client():
    # 初始化 RMT
    rmt = rmt_lr.new_rmt(21, 2, 2046, 1, 0, 0, 2, 255, 13, 2_400, 600)

    buf1 = bytearray(1024 * 100)
    # buf1[:] = bytes([0x80]) * len(buf1)
    buf2 = bytearray(1024 * 100)
    # buf2[:] = bytes([0x80]) * len(buf2)

    server_ip = "192.168.1.5"
    server_port = 30000

    lib_lsl.send(f"尝试连接到 {server_ip}...")
    # 创建标准 TCP Socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_ip, server_port))
    lib_lsl.send("连接成功！")

    i = 0
    while True:
        if i % 2:
            s.readinto(buf1, len(buf1))
            rmt_lr.rmt_send(rmt, buf1, len(buf1))
        else:
            s.readinto(buf2, len(buf2))
            rmt_lr.rmt_send(rmt, buf2, len(buf2))

        while True:
            if rmt_lr.rmt_get_free(rmt) >= 0:
                rmt_lr.rmt_sub_free(rmt, 1)
                break
            time.sleep_us(100)


rmt_sync_client()
