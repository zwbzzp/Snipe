import os
import os.path
import shutil
import time
import datetime

import subprocess


def process():

    delete_files_with_suffix(
        '/home/bitson/projects/phoenix/docs/sphinx/source',
        '.rst',
        ['index.rst']
    )

    copy_files(
        '/home/bitson/projects/phoenix/docs/howto',
        '.rst',
        [],
        '/home/bitson/projects/phoenix/docs/sphinx/source'
    )

    execute_cmd()


def delete_files_with_suffix(source_dir, suffix, exclude_files):

    for file in os.listdir(source_dir):
        file_path = os.path.join(source_dir, file)
        if os.path.isfile(file_path) and file.endswith(suffix) and file not in exclude_files:
            os.remove(file_path)


def copy_files(source_dir, source_suffix, exclude_files, target_dir):

    for file in os.listdir(source_dir):
        if not file.endswith(source_suffix) or file in exclude_files:
            continue

        source_file = os.path.join(source_dir, file)
        target_file = os.path.join(target_dir, file)
        if os.path.isfile(source_file):
            if not os.path.exists(target_dir):  
                os.makedirs(target_dir)  
            if not os.path.exists(target_file) or \
                    (os.path.exists(target_file) and (os.path.getsize(target_file) != os.path.getsize(source_file))):
                open(target_file, "wb").write(open(source_file, "rb").read())


def execute_cmd():
    p = subprocess.call(['make html'], shell=True, cwd='./')

    # p = subprocess.call(['sphinx-build', '-b', 'html', '-d', 'build/doctrees', 'source', 'build/html'], shell=True, cwd='../sphinx')

if __name__ == '__main__':
    process()



