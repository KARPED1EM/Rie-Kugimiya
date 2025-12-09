#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os

from dotenv import load_dotenv
from dotenv.main import DotEnv

from toolbox.json.misc import traverse


class EnvironmentManager(object):
    def __init__(self, path, env, override=False):
        filename = os.path.join(path, '{}.env'.format(env))
        self.filename = filename

        load_dotenv(
            dotenv_path=filename,
            override=override
        )

        self._environ = dict()

    def open_dotenv(self, filename: str = None):
        filename = filename or self.filename
        dotenv = DotEnv(
            dotenv_path=filename,
            stream=None,
            verbose=False,
            interpolate=False,
            override=False,
            encoding="utf-8",
        )
        result = dotenv.dict()
        return result

    def get(self, key, default=None, dtype=str):
        result = os.environ.get(key)
        if result is None:
            if default is None:
                result = None
            else:
                result = default
        else:
            result = dtype(result)
        self._environ[key] = result
        return result


_DEFAULT_DTYPE_MAP = {
    'int': int,
    'float': float,
    'str': str,
    'json.loads': json.loads
}


class JsonConfig(object):
    """
    将 json 中, 形如 `$float:threshold` 的值, 处理为:
    从环境变量中查到 threshold, 再将其转换为 float 类型.
    """
    def __init__(self, dtype_map: dict = None, environment: EnvironmentManager = None):
        self.dtype_map = dtype_map or _DEFAULT_DTYPE_MAP
        self.environment = environment or os.environ

    def sanitize_by_filename(self, filename: str):
        with open(filename, 'r', encoding='utf-8') as f:
            js = json.load(f)

        return self.sanitize_by_json(js)

    def sanitize_by_json(self, js):
        js = traverse(
            js,
            callback=self.sanitize,
            environment=self.environment
        )
        return js

    def sanitize(self, string, environment):
        """支持 $ 符开始的, 环境变量配置"""
        if isinstance(string, str) and string.startswith('$'):
            dtype, key = string[1:].split(':')
            dtype = self.dtype_map[dtype]

            value = environment.get(key)
            if value is None:
                raise AssertionError('environment not exist. key: {}'.format(key))

            value = dtype(value)
            result = value
        else:
            result = string
        return result


def demo1():
    import json

    from project_settings import project_path

    environment = EnvironmentManager(
        path=os.path.join(project_path, 'server/callbot_server/dotenv'),
        env='dev',
    )
    init_scenes = environment.get(key='init_scenes', dtype=json.loads)
    print(init_scenes)
    print(environment._environ)
    return


if __name__ == '__main__':
    demo1()
