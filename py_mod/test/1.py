import socket
import struct
import time

def pack_rmt_symbol(d0, l0, d1, l1):
    """
    根据 ESP32 结构体打包数据:
    duration0 (15bit) | level0 (1bit) | duration1 (15bit) | level1 (1bit)
    """
    part0 = (d0 & 0x7FFF) | ((l0 & 0x1) << 15)
    part1 = (d1 & 0x7FFF) | ((l1 & 0x1) << 15)
    return struct.pack('<HH', part0, part1) # 小端序打包成 4 字节

def start_server():
    server_addr = ('0.0.0.0', 30000)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(server_addr)
    sock.listen(1)
    print("等待 ESP32 连接...")

    while True:
        conn, addr = sock.accept()
        print(f"已连接: {addr}")
        try:
            while True:
                # 示例：生成一段简单的 PWM 波形数据 (100个符号)
                buffer = bytearray()
                for _ in range(4096):
                    buffer.extend(pack_rmt_symbol(100, 1, 100, 0)) # 高100单位, 低100单位
                
                conn.sendall(buffer)
                # time.sleep(1) # 每隔1秒发送一帧
        except Exception as e:
            print(f"连接断开: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    start_server()