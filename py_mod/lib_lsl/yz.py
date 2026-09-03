import _thread


class YZ:
    def __init__(self, value):
        self.value = value
        self._lock = _thread.allocate_lock()

    # 未曾实现方法转接到self.value中,但不加锁
    def __getattr__(self, name):
        def wrapper(*args):
            # with self._lock:
            attr = getattr(self.value, name)
            return attr(*args)

        return wrapper

    # #################引出锁让外部访问################
    def is_lock(self):
        return self._lock.locked()

    def lock(self, 阻塞=1):
        # 无法查到资料，非0都应该是阻塞
        # 无超时参数
        self._lock.acquire(阻塞)

    def rlock(self):
        self._lock.release()

    # 简单实现，用with时不能访问该类的函数了
    # 由于有__getattr__，用内部原始成员变量，原始访问
    def __enter__(self):
        self._lock.acquire()
        return self  # 返回self,外部用 as x,就可以访问到self

    def __exit__(self, exc_type, exc_value, traceback):
        # 假设了release不会出现错误
        self._lock.release()
        return False  # 不吞异常
