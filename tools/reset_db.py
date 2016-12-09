import sys
import os
from subprocess import Popen, PIPE, call
import subprocess

VIRTUAL_ENV_PATH = '/home/bitson/new/env/benv/bin/python3.4'

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/web'))

VERSIONS_DIR = os.path.abspath(os.path.join(WEB_DIR, './migrations/versions'))

MANAGE_DIR = os.path.abspath(os.path.join(WEB_DIR, './manage.py'))

VENV_DIR = os.path.abspath(VIRTUAL_ENV_PATH)

# for doc in os.listdir(VERSIONS_DIR):
#     doc_file = os.path.join(VERSIONS_DIR, doc)
#     if os.path.isfile(doc_file) and doc_file.endswith('py'):
#         os.remove(doc_file)
#
# for doc in os.listdir(WEB_DIR):
#     doc_file = os.path.join(WEB_DIR, doc)
#     if os.path.isfile(doc_file) and doc_file.endswith('sqlite'):
#         os.remove(doc_file)

subprocess.call(['mysql', '-u', 'root', '-padmin123', '', '-e',  'DROP DATABASE phoenix; CREATE DATABASE IF NOT EXISTS phoenix default character set utf8 COLLATE utf8_general_ci'], shell=False)

# print('Running migrate...')
# call([VENV_DIR, MANAGE_DIR, 'db', 'migrate', '-m', '"terminal_03"' ], shell=False, cwd=WEB_DIR)

print('Running upgrade...')
call([VENV_DIR, MANAGE_DIR, 'db', 'upgrade' ], shell=False, cwd=WEB_DIR)

print('Running deploy...')
call([VENV_DIR, MANAGE_DIR, 'deploy' ], shell=False, cwd=WEB_DIR)
