import _thread


class YZ:
    def __init__(self, value):
        self._value = value
        self._lock = _thread.allocate_lock()

    def lock(self):
        self._lock.acquire()

    def rlock(self):
        self._lock.release()

    # 比较并交换,当前值==eq_value,则当前值=new_value
    def eq_and_set(self, eq_value, new_value):
        with self._lock:
            if self._value == eq_value:
                self._value = new_value
                return True
            return False

    # 执行未曾实现的方法
    def __getattr__(self, name):
        def wrapper(*args):
            with self._lock:
                attr = getattr(self._value, name)
                return attr(*args)

        return wrapper

    # list追加
    def append(self, value):
        with self._lock:
            self._value.append(value)

    # list pop
    def pop(self, n):
        with self._lock:
            return self._value.pop(n)

    # dict更新
    def update(self, value):
        with self._lock:
            self._value.update(value)

    # ################无法重载的###################
    def get(self):
        with self._lock:
            return self._value

    def set(self, value):
        with self._lock:
            self._value = value

    #################中括号,需要注意返回值是引用情况###################
    def __getitem__(self, index):
        with self._lock:
            return self._value[index]

    def __setitem__(self, index, value):
        with self._lock:
            self._value[index] = value

    def __delitem__(self, index):
        with self._lock:
            del self._value[index]

    #################无歧义运算符############################
    # +=
    def __iadd__(self, other):
        with self._lock:
            self._value += other
        return self

    # -=
    def __isub__(self, other):
        with self._lock:
            self._value -= other
        return self

    # *=
    def __imul__(self, other):
        with self._lock:
            self._value *= other
        return self

    # /=
    def __itruediv__(self, other):
        with self._lock:
            self._value /= other
        return self

    # //=
    def __ifloordiv__(self, other):
        with self._lock:
            self._value //= other
        return self

    # %=
    def __imod__(self, other):
        with self._lock:
            self._value %= other
        return self

    # **=
    def __ipow__(self, other):
        with self._lock:
            self._value **= other
        return self

    # #################当前锁状态############################
    def locked(self):
        return self._lock.locked()
