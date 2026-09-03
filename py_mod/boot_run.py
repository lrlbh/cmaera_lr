import machine
import time
import _thread
import json
import socket
import struct
from machine import Pin
import neopixel


# 非系统依赖
import lib_lsl
import boot_config
from lib_lsl import tl


需要查看的文件 = []


# 收: 4字节文件个数 + [4字节文件名长度 + 文件名 + 4字节文件内容长度 + 文件内容] * 文件个数
# 增加一个，一百万是查看文件申请,不合理协议化了
# 因为除了查看应该不会增加了，使用内置脚本处理其他操作应该更合理
# 查看文件: 4字节一百万 + 4字节文件个数(0) + [4字节文件名长度 + 文件名] * 文件个数
def read(sock, 需要查看的文件):
    """
    暂不处理，但别忘了
        - 非S3,文件太大爆内存
        - 存在大量数据重复拷贝
    """

    try:
        while True:
            # 文件个数
            file_n = tl.read_exact(sock, 4)
            file_n = int.from_bytes(file_n, "big")

            # 重启
            if file_n == 0 and boot_config.无文件时_更新是否重启:
                machine.reset()

            # 误操作
            if file_n == 0:
                lib_lsl.send_war("文件数量0, 不更新")
                continue

            # 申请查看文件
            if file_n == 1000000:
                file_n = tl.read_exact(sock, 4)
                file_n = int.from_bytes(file_n, "big")
                for _ in range(file_n):
                    file_name_len = int.from_bytes(tl.read_exact(sock, 4), "big")
                    file_name = tl.read_exact(sock, file_name_len).decode()
                    需要查看的文件.append(file_name)
                    lib_lsl.send_war("申请查看文件:")
                for file in 需要查看的文件:
                    lib_lsl.send_war(f"\t {file}")
                continue

            # 申请更新文件
            for _ in range(file_n):
                lib_lsl.send_war(f"需要更新文件数量:{file_n}")

                t0 = time.ticks_ms()
                # 获取文件名
                file_name_len = int.from_bytes(tl.read_exact(sock, 4), "big")
                file_name = tl.read_exact(sock, file_name_len).decode()
                tl.mkdir(file_name)

                # 创建文件
                with open(file_name, "wb") as f:
                    file_data_len = int.from_bytes(tl.read_exact(sock, 4), "big")
                    写入数量 = f.write(tl.read_exact(sock, file_data_len))

                lib_lsl.send_war(
                    f"{file_name} -> size: {写入数量 / 1024:0.2f}KiB -> 耗时:{time.ticks_diff(time.ticks_ms(), t0)}ms"
                )

            lib_lsl.send_war("更新成功")
            time.sleep_ms(20)  # 尽量保证 更新成功 发送完成
            machine.reset()
    except Exception as e:
        lib_lsl.send_err(f"tcp读取处: {tl.get_完整错误信息(e)}")
        sock.close()


# 子线程
def 子线程():

    # 提示灯
    rgb = neopixel.NeoPixel(machine.Pin(boot_config.boot_pin, machine.Pin.OUT), 1)
    rgb[0] = (0, 0, 0)
    rgb.write()

    # 连接wifi
    rgb[0] = boot_config.rgb_msg.连接wifi中
    rgb.write()
    t0 = time.ticks_ms()
    wifi = lib_lsl.WIFI(
        account=boot_config.wifi信息组,
        static=boot_config.静态ip,
        ip=boot_config.ip,
        子网掩码=boot_config.子网掩码,
        网关=boot_config.网关,
        dns_server=boot_config.dns_server,
    )
    wifi.conn_one(
        boot_config.ssid, boot_config.pwd
    )  # 人为阻塞连一下，为了计算连接wifi耗时
    wifi.conn_thr(boot_config.ssid, boot_config.pwd)
    t_log = f"连接wifi耗时: {time.ticks_diff(time.ticks_ms(), t0)} ms"

    # 获取广播的服务器IP地址
    rgb[0] = boot_config.rgb_msg.获取服务器地址中
    rgb.write()
    t0 = time.ticks_ms()
    ip, 更新端口, 日志端口 = None, None, None
    while True:
        try:
            ip, 更新端口, 日志端口 = tl.get_ip_更新服务器(boot_config.广播端口)
            break
        except:
            time.sleep_ms(500)
    更新端口 = int(更新端口)
    日志端口 = int(日志端口)

    # 开启日志打印
    lib_lsl.set_config(ip=ip, port=日志端口, udp=True)

    # 打印累积日志
    lib_lsl.send_war(f"\n\n\n{'-' * 99}")
    lib_lsl.send_war(t_log)
    # lib_lsl.send_war(id(wifi))
    lib_lsl.send_war(
        f"获取server_ip耗时: {time.ticks_diff(time.ticks_ms(), t0)}ms addr: {ip}:{日志端口}"
    )

    # 获取本地文件hash,并且补个头
    rgb[0] = boot_config.rgb_msg.获取md5中
    rgb.write()
    t0 = time.ticks_ms()
    file_md5 = tl.get_files_md5("/", boot_config.忽略的文件和目录)
    # for key in tl.get_files_md5("/"):
    #     lib_lsl.send_err(key," --> ",tl.get_files_md5("/")[key])
    file_md5 = json.dumps(file_md5).encode()
    file_md5 = struct.pack("!I", len(file_md5)) + file_md5
    lib_lsl.send_war(f"获取md5耗时: {time.ticks_diff(time.ticks_ms(), t0)} ms")

    # 维持更新套接字连接状态
    global 需要查看的文件
    while True:
        rgb[0] = boot_config.rgb_msg.连接更新服务器中
        rgb.write()
        lib_lsl.send_war("尝试一次tcp连接")

        # 建立tcp连接
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, 更新端口))
        except Exception as e:
            lib_lsl.send_err(f"tcp意外错误: {e}")
            if sock:
                sock.close()
            time.sleep_ms(300)
            continue

        # 连接成功关灯
        rgb[0] = (0, 0, 0)
        rgb.write()

        # 创建读线程
        lib_lsl.Thread.create_thread(read, (sock, 需要查看的文件), stack_size=4096)

        # 发
        # 增加一个，一百万是发送文件
        # 因为除了查看应该不会增加了，使用内置脚本处理其他操作应该更合理，不合理协议化了
        # 发送文件: 4字节一百万 + 4字节文件个数 + [4字节文件名长度 + 文件名] * 文件个数
        try:
            while True:
                # 心跳间隔,先延迟不然服务器可能错误关闭连接
                time.sleep_ms(boot_config.心跳间隔ms)

                # 向服务器发送文件
                if 需要查看的文件:
                    temp需要查看的文件 = 需要查看的文件.copy()  # 避免在发送过程中被修改
                    需要查看的文件 = []

                    # 弄陀屎,因为不需要扩展协议了,这里一百万表示发送文件
                    # 据说不用sendall,因为阻塞套接字下完全相同
                    # 非阻塞下sendall未定义行为,write返回实际写入字节
                    sock.write(struct.pack("!I", 1000000))

                    # 发送文件个数
                    sock.write(struct.pack("!I", len(temp需要查看的文件)))

                    for file_name in temp需要查看的文件:
                        # 发送文件名长度
                        sock.write(struct.pack("!I", len(file_name)))

                        # 发送文件名
                        sock.write(file_name.encode())

                        # 发送文件内容长度 + 文件内容
                        with open(file_name, "rb") as f:
                            file_content = f.read()
                            sock.write(struct.pack("!I", len(file_content)))
                            sock.write(file_content)

                # 心跳
                sock.write(file_md5)

        except Exception as e:
            lib_lsl.send_err(f"tcp断开: {tl.get_完整错误信息(e)}")
            sock.close()


def run():

    # 浮空boot引脚     执行     boot.py
    # 强上拉boot引脚   不执行   boot.py
    boot_p = Pin(boot_config.boot_pin, Pin.IN, Pin.PULL_DOWN)
    if boot_p.value():
        return

    # 子线程用于更新
    lib_lsl.Thread.create_thread(子线程, (), stack_size=4096)
    # 子线程()

    # 获取到server_ip后在运行main
    while lib_lsl._ul.ip is None:
        time.sleep_ms(50)

    # 主线程运行main
    try:
        import main
    except Exception as e:
        # 用户错误返回完整错误信息
        lib_lsl.send_err(tl.get_完整错误信息(e))
        raise Exception("异常结束,但避免系统调用main")

    lib_lsl.send("脚本正常结束")
    raise Exception("正常结束,但避免系统调用main")
