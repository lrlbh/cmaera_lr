import time

import socket
import lib_lsl
import adc_lsl.tl
import adc_lsl
import machine

lib_lsl.send(adc_lsl.tl.get_支持的校准模式())

SERVER_IP = "192.168.1.5"
SERVER_PORT = 8888


adc = adc_lsl.ADC_连续(
    pins=[9],
    attens=[0],
    采样频率=8333,
    buf_size=8192 * 5,
    每帧大小=8192,
).start()
 
while True:
    try:
        # ---- TCP ----
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 发送超时5秒，防止永久阻塞
        sock.connect((SERVER_IP, SERVER_PORT))
        lib_lsl.send(f"已连接 {SERVER_IP}:{SERVER_PORT}")

        while True:
            # lib_lsl.send(11)
            sock.sendall(adc.get_data_p())
    except Exception as e:
        lib_lsl.send(f"连接死亡: {e}")
        time.sleep(1)
