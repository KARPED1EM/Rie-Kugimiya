#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path

from toolbox.os.environment import EnvironmentManager


project_path = os.path.abspath(os.path.dirname(__file__))
project_path = Path(project_path)


environment = EnvironmentManager(
    path=os.path.join(project_path, 'dotenv'),
    env=os.environ.get('environment', 'dev'),
)


if __name__ == '__main__':
    pass
