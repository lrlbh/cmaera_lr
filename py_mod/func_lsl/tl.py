import os

import boot_config
import lib_lsl
import lib_lsl.tl


# def delete_all1(参考config=True):
#     files_all = lib_lsl.tl.get_files_path("/")
#     if 参考config is True:
#         files = lib_lsl.tl.get_files_path("/", boot_config.忽略的文件和目录)
#     else:
#         files = files_all

#     lib_lsl.send("删除文件:")
#     for file in files:
#         lib_lsl.send(file)
#         os.remove(file)

#     lib_lsl.send(f"总文件数量:{len(files_all)}")
#     lib_lsl.send(f"删除文件数量:{len(files)}")
#     lib_lsl.send(f"剩余文件数量:{len(files_all) - len(files)}")
#     剩余文件 = list(set(files_all) - set(files))
#     lib_lsl.send("剩余文件:")
#     for file in 剩余文件:
#         lib_lsl.send(file)


def delete_all(参考config=True):

    all_dir, all_file = lib_lsl.tl.get_目录和文件的数量("/")

    def is_dir(path):
        return bool(os.stat(path)[0] & 0x4000)

    files_all = lib_lsl.tl.get_files_path("/")

    if 参考config:
        删除集合 = set(lib_lsl.tl.get_files_path("/", boot_config.忽略的文件和目录))
    else:
        删除集合 = set(files_all)

    删除文件数量 = 0
    删除目录数量 = 0

    def remove_tree(path="/", prefix=""):

        nonlocal 删除文件数量, 删除目录数量

        items = os.listdir(path)

        for i, name in enumerate(items):
            last = i == len(items) - 1

            full = path.rstrip("/") + "/" + name

            char = "└── " if last else "├── "

            if is_dir(full):
                # 不进入目录
                if 参考config and name in boot_config.忽略的文件和目录:
                    # lib_lsl.send(prefix + char + name + "/[忽略]")
                    continue

                # 目录本身
                lib_lsl.send(prefix + char + name + "/")

                # 进入目录
                remove_tree(full, prefix + ("    " if last else "│   "))

                info_msg = "ERROR目录:"
                try:
                    os.rmdir(full)
                    删除目录数量 += 1
                    info_msg = "删除目录:"
                except OSError as e:
                    if e.args[0] == 39:
                        info_msg = "非空目录:"
                    else:
                        raise
                finally:
                    # 确保失败情况下，打印在在前，ERROR抛出在后
                    lib_lsl.send(
                        prefix
                        + ("    " if last else "│   ")
                        + f"└── {info_msg} "
                        + name
                    )

            elif full in 删除集合:
                # 确保失败情况下，打印在在前，ERROR抛出在后
                lib_lsl.send(prefix + char + name)

                os.remove(full)

                删除文件数量 += 1

    lib_lsl.send("开始删除:")

    try:
        remove_tree("/")
    except Exception as e:
        lib_lsl.send_err(lib_lsl.tl.get_完整错误信息(e))

    # -------------------不是我写的输出下校验看看---------------------
    lib_lsl.send("---------------------------------------------------")
    lib_lsl.send("校验:")
    this_dir, this_file = lib_lsl.tl.get_目录和文件的数量("/")

    send_msg = f"总目录:{all_dir} 删除目录:{删除目录数量} 剩余目录:{this_dir}"
    if all_dir - this_dir == 删除目录数量:
        lib_lsl.send(send_msg)
    else:
        lib_lsl.send_err(send_msg)

    send_msg = f"总文件:{all_file} 删除文件:{删除文件数量} 剩余文件:{this_file}"
    if all_file - this_file == 删除文件数量:
        lib_lsl.send(send_msg)
    else:
        lib_lsl.send_err(send_msg)

    # -------------------输出剩余文件---------------------
    lib_lsl.send("---------------------------------------------------")
    lib_lsl.send("剩余文件:")

    def print_tree(path, prefix=""):
        items = os.listdir(path)

        items.sort()
        total = len(items)
        for idx, name in enumerate(items):
            is_last = idx == total - 1
            full = path + "/" + name
            st = os.stat(full)
            # 判断目录：st[0] & 0x4000
            is_dir = False
            if st and (st[0] & 0x4000):
                is_dir = True
            # 分支符号
            branch = "└── " if is_last else "├── "
            # 目录末尾加 /
            display_name = name + "/" if is_dir else name
            lib_lsl.send(prefix + branch + display_name)
            # 如果是目录递归，生成下一层前缀
            if is_dir:
                # 最后一项用空格，非最后一项保留竖线 │
                new_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(full, new_prefix)

    try:
        print_tree("/")
    except Exception as e:
        lib_lsl.send_err(lib_lsl.tl.get_完整错误信息(e))
