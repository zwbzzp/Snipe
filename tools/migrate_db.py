# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 6/24/16 bitson : Init

import sys
import os
from subprocess import Popen, PIPE, call
import subprocess

VIRTUAL_ENV_PATH = '/usr/bin/python3.4'

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/web'))

VERSIONS_DIR = os.path.abspath(os.path.join(WEB_DIR, './migrations/versions'))

MANAGE_DIR = os.path.abspath(os.path.join(WEB_DIR, './manage.py'))

VENV_DIR = os.path.abspath(VIRTUAL_ENV_PATH)


subprocess.call(['mysql', '-u', 'root', '-padmin123', '', '-e',  'DROP DATABASE phoenix; CREATE DATABASE IF NOT EXISTS phoenix default character set utf8 COLLATE utf8_general_ci'], shell=False)

print('Running upgrade...')
call([VENV_DIR, MANAGE_DIR, 'db', 'upgrade' ], shell=False, cwd=WEB_DIR)

print('Running migrate...')
call([VENV_DIR, MANAGE_DIR, 'db', 'migrate', '-m', '"hostinfo_03"' ], shell=False, cwd=WEB_DIR)

print('Running upgrade...')
call([VENV_DIR, MANAGE_DIR, 'db', 'upgrade' ], shell=False, cwd=WEB_DIR)

print('Running deploy...')
call([VENV_DIR, MANAGE_DIR, 'deploy' ], shell=False, cwd=WEB_DIR)
