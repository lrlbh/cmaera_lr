import time

import socket

from dac_lsl import RMT
import lib_lsl

from lib_lsl import WIFI

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
    driver = RMT(gpio=48, 缓冲区长度=4096, 缓冲区数量=3)

    server_ip = "192.168.1.5"
    server_port = 30000

    lib_lsl.send(f"尝试连接到 {server_ip}...")
    # 创建标准 TCP Socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_ip, server_port))
    lib_lsl.send("连接成功！")

    mem_buf_1 = driver.get_mem()
    mem_buf_2 = driver.get_mem()
    mem_buf_3 = driver.get_mem()

    if s.readinto(mem_buf_1) != 4096 * driver.symbol_size:
        lib_lsl.send("错误长度")
    if s.readinto(mem_buf_2) != 4096 * driver.symbol_size:
        lib_lsl.send("错误长度")
    if s.readinto(mem_buf_3) != 4096 * driver.symbol_size: 
        lib_lsl.send("错误长度")

    driver.return_mem(mem_buf_1)
    driver.return_mem(mem_buf_2)
    driver.return_mem(mem_buf_3)

    while True:
        mem_buf = driver.get_mem(1)
        driver.return_mem(mem_buf)


rmt_sync_client()

