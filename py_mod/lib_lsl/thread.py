import lib_lsl
import _thread


class Thread:
    thread_num = lib_lsl.YZ(0)

    @classmethod
    def create_thread(cls, func, args=(), kwargs=None, stack_size=0):
        """
        创建 MicroPython 线程

        :param func: 线程执行函数
        :param args: 位置参数(tuple)
        :param kwargs: 关键字参数(dict)
        :param stack_size: 线程栈大小(bytes) 0就是用默认大小,S3默认5K
        """

        if kwargs is None:
            kwargs = {}

        # 包装函数：线程退出（正常/抛异常）都会执行计数减1
        def thread_wrapper(*inner_args, **inner_kwargs):
            try:
                func(*inner_args, **inner_kwargs)
            finally:
                # 无论正常退出还是异常崩溃，都会进到这里
                with cls.thread_num:
                    cls.thread_num.value -= 1

        # 创建线程
        with cls.thread_num:
            _thread.stack_size(stack_size)
            cls.thread_num.value += 1
            try:
                ret = _thread.start_new_thread(thread_wrapper, args, kwargs)
            except Exception:
                cls.thread_num.value -= 1
                raise

        return ret

    # def create_thread(func):
    #     def wrapper(*args, **kwargs):
    #         # 调用前执行
    #         result = func(*args, **kwargs)
    #         # 调用后执行
    #         return result

    #     return wrapper
