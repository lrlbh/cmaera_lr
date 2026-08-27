"""
将boot.py编译进入固件后,用户上传的boot.py无法覆盖
正常.py是可以覆盖的,不知道是否因为boot.py或者类似功能文件,比较特殊
所以为了可以修改boot.py在这里多一级调用

在 /micropython/ports/esp32/modules/_boot.py || inisetup.py 中
也可以创建烧录固件后,第一次创建文件系统时,自动创建可覆盖的boot.py
"""

import boot_run

boot_run.run()
