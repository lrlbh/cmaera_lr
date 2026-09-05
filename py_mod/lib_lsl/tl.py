import binascii

import hashlib

import os
import io
import sys
import socket
import json
import lib_lsl.ul


def prin_tree(path="/", indent="", max_depth=None, show_hidden=False):
    """打印目录树（MicroPython 版）

    path        起始目录，默认根目录 "/"
    indent      内部递归用，勿传
    max_depth   最大递归深度，None 表示不限
    show_hidden 是否显示以 . 开头的文件
    """

    if max_depth is not None and max_depth < 0:
        return

    # entries = sorted(os.listdir(path))
    entries = os.listdir(path)

    if not show_hidden:
        entries = [e for e in entries if not e.startswith(".")]

    items = []
    for e in entries:
        full = path.rstrip("/") + "/" + e
        is_dir = bool(os.stat(full)[0] & 0x4000)  # S_IFDIR，失败直接抛
        items.append((e, is_dir))

    for name, is_dir in items:
        lib_lsl.ul.send(indent + "├── " + name + ("/" if is_dir else ""))
        if is_dir:
            prin_tree(
                path.rstrip("/") + "/" + name,
                indent + "│    ",
                None if max_depth is None else max_depth - 1,
                show_hidden,
            )


def read_exact(sock, length):
    """
    tcp一次读够
    """
    data = bytearray(length)
    view = memoryview(data)

    offset = 0

    while offset < length:
        n = sock.readinto(view[offset:])

        if n is None:
            continue

        if n == 0:
            raise OSError("socket closed")

        offset += n

    return data


def readinto_exact(sock, buf, length=None):
    """
    TCP一次读取够
    """
    if length is None:
        length = len(buf)

    view = memoryview(buf)

    offset = 0

    while offset < length:
        n = sock.readinto(view[offset:length])

        if n is None:
            continue

        if n == 0:
            raise OSError("socket closed")

        offset += n

    return offset


def get_ip_更新服务器(广播端口=50000):
    """
    返回: ip,更新端口,日志端口
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 广播端口))
        while True:
            data, addr = sock.recvfrom(1024)
            data = json.loads(data.decode())
            return addr[0], data["更新端口"], data["日志端口"]
    finally:
        sock.close()


def file_exists(path):
    """判断文件是否存在"""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def mkdir(path):
    """确保文件所在目录存在，不存在则递归创建,必须携带文件名或者分隔符/aa/bb/"""
    dir_path = path.rsplit("/", 1)[0]
    if not dir_path:
        return  # 文件在根目录，直接返回

    parts = dir_path.strip("/").split("/")
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            os.stat(cur)
        except OSError:
            os.mkdir(cur)


def build_url(base, path, params=None):
    """
    拼接中文URL:
    - base = "192.168.1.1:50000"
    - path = "/中文接口地址"
    - params字典中的key和value会进行URL编码
    """

    def url_encode(s):
        if not isinstance(s, str):
            s = str(s)
        res = []
        for ch in s:
            code = ord(ch)
            # RFC3986 unreserved: A-Z a-z 0-9 -_.~
            if (
                (48 <= code <= 57)
                or (65 <= code <= 90)
                or (97 <= code <= 122)
                or ch in "-_.~"
            ):
                res.append(ch)
            else:
                for b in ch.encode("utf-8"):
                    res.append("%%%02X" % b)
        return "".join(res)

    # 处理路径
    encoded_path = "/".join(url_encode(p) for p in path.split("/"))
    url = base.rstrip("/") + "/" + encoded_path

    # 处理查询参数
    if params:
        query = "&".join(f"{url_encode(k)}={url_encode(v)}" for k, v in params.items())
        url += "?" + query

    return url


def get_完整错误信息(e):
    buf = io.StringIO()
    sys.print_exception(e, buf)  # type: ignore
    s = buf.getvalue()
    buf.close()

    return s


def get_目录和文件的数量(path):
    total_dir = 0
    total_file = 0
    for name in os.listdir(path):
        full = path + "/" + name
        st = os.stat(full)
        if st[0] & 0x4000:
            total_dir += 1
            # 递归进入子目录
            subd, subf = get_目录和文件的数量(full)
            total_dir += subd
            total_file += subf
        else:
            total_file += 1
    return total_dir, total_file


# 返回文件保证路径+名称 列表
def get_files_path(path, ignore=None):

    ret = []

    if ignore is None:
        ignore = []

    ignore_set = set(ignore)

    def walk(path):

        try:
            items = os.listdir(path)
        except:
            return

        for name in items:
            if name in ignore_set:
                continue

            if path == "/":
                full_path = "/" + name
            else:
                full_path = path + "/" + name

            try:
                stat = os.stat(full_path)

                # 目录
                if stat[0] & 0x4000:
                    walk(full_path)

                # 文件
                else:
                    ret.append(full_path)

            except:
                pass

    walk(path)

    return ret


# 返回文件名称列表
def get_files_name(path, ignore=None):

    paths = get_files_path(path, ignore)

    ret = []

    for p in paths:
        ret.append(p[p.rfind("/") + 1 :])

    return ret


def get_files_md5(root_dir, ignore_list=None):
    ignore_set = set(ignore_list) if ignore_list else set()
    result = {}
    stack = [(root_dir, "")]

    # 预分配缓冲区，减少循环内内存分配
    # 4096 字节通常是性能与内存的最佳平衡点
    buf_size = 4096
    read_buf = bytearray(buf_size)

    while stack:
        curr_path, rel_prefix = stack.pop()
        # ilistdir 返回迭代器，元素为 (name, type, inode, ...)
        # type: 0x4000 为目录, 0x8000 为普通文件
        for entry in os.ilistdir(curr_path):
            name = entry[0]
            etype = entry[1]

            if name in ignore_set:
                continue

            # 尽量减少字符串操作
            full_path = curr_path + "/" + name
            rel_path = (rel_prefix + "/" + name) if rel_prefix else name

            if etype & 0x4000:  # 目录
                stack.append((full_path, rel_path))
            elif etype & 0x8000:  # 文件
                h = hashlib.md5()
                with open(full_path, "rb") as f:
                    while True:
                        # 使用 readinto 比 read 更快，因为它直接写在预分配的内存中
                        n = f.readinto(read_buf)
                        if n == 0:
                            break
                        if n == buf_size:
                            h.update(read_buf)
                        else:
                            h.update(memoryview(read_buf)[:n])

                # 只有在最后存入字典时处理 key 格式
                result["/" + rel_path] = binascii.hexlify(h.digest()).decode()

    return result


# def get_files_md5(root_dir, ignore_list=None):
#     """
#     返回 {"/相对路径": MD5字符串}
#     """
#     if ignore_list is None:
#         ignore_list = []
#     ignore_set = set(ignore_list)
#     result = {}

#     def join_path(p1, p2):
#         # 简单路径拼接
#         if p1.endswith("/"):
#             return p1 + p2
#         else:
#             return p1 + "/" + p2

#     def is_file(path):
#         try:
#             return (os.stat(path)[0] & 0x4000) == 0  # 0x4000 表示目录
#         except OSError:
#             return False

#     def walk(path, rel_prefix=""):
#         try:
#             items = os.listdir(path)
#         except OSError:
#             return

#         for name in items:
#             if name in ignore_set:
#                 continue

#             full_path = join_path(path, name)
#             rel_path = join_path(rel_prefix, name) if rel_prefix else name
#             if is_file(full_path):
#                 # 计算MD5
#                 # s = time.ticks_ms()
#                 h = hashlib.md5()
#                 with open(full_path, "rb") as f:
#                     h.update(f.read())
#                 key = "/" + rel_path.replace("\\", "/")
#                 result[key] = binascii.hexlify(h.digest()).decode()
#                 # print(key,time.ticks_ms()-s)
#             else:
#                 walk(full_path, rel_path)

#     walk(root_dir)
#     return result
