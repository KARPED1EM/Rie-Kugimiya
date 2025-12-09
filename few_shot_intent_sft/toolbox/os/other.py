import os
import inspect


def pwd():
    """你在哪个文件调用此函数, 它就会返回那个文件所在的 dir 目标"""
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    return os.path.dirname(os.path.abspath(module.__file__))
