#!/usr/bin/python3
# -*- coding: utf-8 -*-
from typing import Callable


def traverse(js, callback: Callable, *args, **kwargs):
    if isinstance(js, list):
        result = list()
        for l in js:
            l = traverse(l, callback, *args, **kwargs)
            result.append(l)
        return result
    elif isinstance(js, tuple):
        result = list()
        for l in js:
            l = traverse(l, callback, *args, **kwargs)
            result.append(l)
        return tuple(result)
    elif isinstance(js, dict):
        result = dict()
        for k, v in js.items():
            k = traverse(k, callback, *args, **kwargs)
            v = traverse(v, callback, *args, **kwargs)
            result[k] = v
        return result
    elif isinstance(js, int):
        return callback(js, *args, **kwargs)
    elif isinstance(js, str):
        return callback(js, *args, **kwargs)
    else:
        return js


def demo1():
    d = {
        "env": "ppe",
        "mysql_connect": {
            "host": "$mysql_connect_host",
            "port": 3306,
            "user": "callbot",
            "password": "NxcloudAI2021!",
            "database": "callbot_ppe",
            "charset": "utf8"
        },
        "es_connect": {
            "hosts": ["10.20.251.8"],
            "http_auth": ["elastic", "ElasticAI2021!"],
            "port": 9200
        }
    }

    def callback(s):
        if isinstance(s, str) and s.startswith('$'):
            return s[1:]
        return s

    result = traverse(d, callback=callback)
    print(result)
    return


if __name__ == '__main__':
    demo1()
