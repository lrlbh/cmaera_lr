# wifilr.pyi
# MicroPython user C module - wifi helper

from typing import List

def get_ipv6() -> None:
    """
    申请 IPv6 link-local 地址
    """
    ...

def get_ipv6_addr() -> List[str]:
    """
    返回当前所有 IPv6 地址
    返回:
        List[str]
    """
    ...