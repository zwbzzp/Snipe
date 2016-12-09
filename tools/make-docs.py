# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.. All rights reserved.
#
# 20160112 fengyingcai : Create a make doc script to help developers to build
#                        documents in docs/ to html or pdf , etc.


import sys
import os
import subprocess
import shutil

TOOLS_DIR = os.path.abspath(os.path.dirname(__file__))
DOCS_DIR = os.path.abspath(os.path.join(TOOLS_DIR, '../docs'))

SPHINX_DIR = os.path.abspath(os.path.join(DOCS_DIR, 'sphinx'))
SPHINX_SOURCE_DIR = os.path.abspath(os.path.join(SPHINX_DIR, 'source'))

DEVELOP_DIR = os.path.abspath(os.path.join(DOCS_DIR, 'develop'))
HOWTO_DIR = os.path.abspath(os.path.join(DOCS_DIR, 'howto'))
MANUAL_DIR = os.path.abspath(os.path.join(DOCS_DIR, 'manual'))

# all docs directories
DOCS_DIRS = [HOWTO_DIR]

# which make command
if sys.platform.startswith('win'):
    MAKE = 'make.bat'
    USE_SHELL = True
elif sys.platform.startswith('linux'):
    MAKE = 'make'
    USE_SHELL = False


def prepare_docs():
    """ Prepare all docs, copy to SPHINX_SOURCE_DIR
    :return:
    """
    for doc in os.listdir(HOWTO_DIR):
        doc_file = os.path.join(HOWTO_DIR, doc)
        if os.path.isfile(doc_file) and doc_file.endswith('rst'):
            shutil.copy(doc_file, SPHINX_SOURCE_DIR)


def make_html():
    """ Make html version documents
    :return:
    """
    return subprocess.call([MAKE, 'html'], shell=USE_SHELL, cwd=SPHINX_DIR)


def make_all():
    """ Make all version documents
    :return:
    """
    prepare_docs()
    make_html()


def make_clean():
    """ Clean all
    :return:
    """
    subprocess.call([MAKE, 'clean'], shell=USE_SHELL, cwd=SPHINX_DIR)


def main(argv):
    make_all()


if __name__ == '__main__':
    main(sys.argv)
