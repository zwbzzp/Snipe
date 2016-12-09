# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-9 qinjinghui : Init

import os
import sys
import re

# Fix path problem
basedir = os.path.abspath(os.path.dirname(__file__))
os.chdir(basedir)
sys.path.append(basedir)
sys.path.append(os.path.join(basedir, '..'))

# Import environment variables
env_file_path = os.path.join(basedir, '.env')
if os.path.exists(env_file_path):
    print('Importing environment from .env...')
    env = {}
    for line in open(env_file_path):
        line = line.strip()
        # Skip comments
        if re.match('^\s*#', line):
            continue
        try:
            idx = line.index('=')
        except:
            continue
        if idx+1 == len(line):
            continue
        env[line[:idx]] = line[idx+1:]
    os.environ.update(env)


from app import app, db
from app.models import User, Role
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand

#app = create_app(os.getenv('FLASK_CONFIG') or 'default')

manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role)

manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

@app.teardown_request
def teardown_request(exec):
    print('***** teardown request *****')


@manager.command
def deploy():
    """Run deployment tasks."""
    import datetime
    from flask.ext.migrate import upgrade
    from app.models import Role, User

    # migrate database to latest revision
    upgrade()

    # init data
    Role.insert_default_roles()
    User.insert_default_users()


    app.logger.info("Deploy finished at %s." % datetime.datetime.now())

@manager.command
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

@manager.command
def runserver():
    app.run(host='0.0.0.0', port=8001)

if __name__ == '__main__':
    manager.run()