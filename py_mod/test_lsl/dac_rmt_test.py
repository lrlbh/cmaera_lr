import socket

from dac_lsl import RMT
import lib_lsl

from lib_lsl import WIFI


WIFI().conn_one()


server_ip = "192.168.1.5"
server_port = 30000


# 创建标准 TCP Socket
lib_lsl.send(f"尝试连接到 {server_ip}...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((server_ip, server_port))

rmt = RMT(gpio=21, freq_khz=24)


while True:
    buf = rmt.get_mem()
    data_len = s.readinto(buf, len(buf))
    rmt.return_mem(buf, data_len)
    lib_lsl.send(f"本次长度 {data_len}...")
