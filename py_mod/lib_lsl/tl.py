import binascii

import hashlib

import os
import io
import sys


def file_exists(path):
    """ 判断文件是否存在 """
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
            if (48 <= code <= 57) or (65 <= code <= 90) or (97 <= code <= 122) or ch in "-_.~":
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
        query = "&".join(
            f"{url_encode(k)}={url_encode(v)}" for k, v in params.items())
        url += "?" + query

    return url


def get_完整错误信息(e):
    buf = io.StringIO()
    sys.print_exception(e, buf) # type: ignore
    s = buf.getvalue()
    buf.close()

    return s


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
