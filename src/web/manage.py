# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.

import os
import sys
import re
import codecs

# Fix system encoding
# if sys.version_info.major == 2:
#     if hasattr(sys.stdout, 'encoding'):
#         if sys.stdout.encoding.lower() != 'utf-8':
#             sys.stdout = codecs.getwriter('utf-8')(sys.stdout, 'strict')
#     if hasattr(sys.stderr, 'encoding'):
#         if sys.stderr.encoding.lower() != 'utf-8':
#             sys.stderr = codecs.getwriter('utf-8')(sys.stderr, 'strict')
# if sys.version_info.major == 3:
#     if hasattr(sys.stdout, 'encoding'):
#         if sys.stdout.encoding.lower() != 'utf-8':
#             sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
#     if hasattr(sys.stderr, 'encoding'):
#         if sys.stderr.encoding.lower() != 'utf-8':
#             sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

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
from app.celery_sqlalchemy_scheduler import DatabaseScheduler
from app.models import User

from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand

manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db)


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@app.teardown_request
def teardown_request(exec):
    db.session.flush()
    print('***** teardown request *****')


@app.before_request
def before_request(*args, **kwargs):
    print('***** before request *****')


@app.teardown_appcontext
def teardown_appcontext(*args, **kwargs):
    db.session.flush()
    print('***** teardown appcontext *****')


####################
# celery
####################

from celery import Celery, Task


class BoundTask(Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        if app.config.get('CELERY_ALWAYS_EAGER'):
            return super(BoundTask, self).__call__(*args, **kwargs)
        else:
            with app.app_context():
                print('***** flask app context injected *****')
                db.session.flush()
                return super(BoundTask, self).__call__(*args, **kwargs)

celery = Celery(app.import_name, broker=app.config.get('CELERY_BROKER_URL'),
                backend=app.config.get('CELERY_RESULT_BACKEND'),
                set_as_current=True, task_cls=BoundTask)
celery.conf.update(app.config)


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware

    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


@manager.command
def deploy():
    """Run deployment tasks."""
    import datetime
    from flask.ext.migrate import upgrade
    from app.models import Role, User, Period, Course,  Parameter, \
        Protocol, Image, Flavor, Policy

    # migrate database to latest revision
    upgrade()

    # init data
    Role.insert_default_roles()
    User.insert_default_users()
    if Period.query.count() <= 0:
        Period.insert_default_periods()
    Parameter.insert_default_params()
    Protocol.insert_all_protocols()
    Policy.insert_default_policy()

    # init local floating ip
    from phoenix.db import init_db
    init_db.init()

    from app.celery_sqlalchmey_scheduler_models import DatabaseSchedulerEntry, \
        CrontabSchedule, IntervalSchedule

    DatabaseSchedulerEntry.query.delete()
    CrontabSchedule.query.delete()
    IntervalSchedule.query.delete()

    # interval 1 minute
    interval = IntervalSchedule()
    interval.period = 'minutes'
    interval.every = 1
    db.session.add(interval)
    # lesson interval schedule
    for entry in ['schedule_start_lesson', 'schedule_clean_desktops',]:
                  # 'schedule_task_build_desktop', 'schedule_task_wait_state',
                  # 'schedule_task_floating', 'schedule_task_detect_desktop',
                  #'schedule_task_delete_desktop']:
        dse = DatabaseSchedulerEntry()
        dse.name = entry
        dse.task = entry
        dse.enabled = True
        dse.interval = interval
        db.session.add(dse)

    sync_openstack()
    Image.insert_all_images()
    Flavor.insert_all_flavors()

    app.logger.info("Deploy finished at %s." % datetime.datetime.now())


@manager.command
def sync_openstack():
    """Run sync local floating ip"""
    from phoenix.cloud.openstack.sync_openstack import floating_ip_manager
    floating_ip_manager.clean()
    floating_ip_manager.refresh()


@manager.command
def worker(loglevel='info'):
    """Run celery worker."""
    from celery.bin.worker import main as worker_main

    from celery import platforms
    
    platforms.C_FORCE_ROOT = True   # FIXME: need root to run celery, change it


    sys.argv = [sys.argv[0], '-l', loglevel]
    worker_main(celery)


@manager.command
def beat(Scheduler='manage.DatabaseScheduler', loglevel='info'):
    """Run celery beat."""
    from celery.bin.beat import main as beat_main

    sys.argv = [sys.argv[0], '-S', Scheduler, '-l', loglevel]
    with app.app_context():
        beat_main(celery)


def insert_roles():
    from app.models import Role

    roles = ['Student', 'Teacher', 'Administrator']

    for role in roles:
        if Role.query.filter_by(name=role).first() is None:
            r = Role(name=role)
            db.session.add(r)
    db.session.commit()


def insert_users():
    from app.models import User, Role

    student = Role.query.filter_by(name='Student').first()
    teacher = Role.query.filter_by(name='Teacher').first()
    admin = Role.query.filter_by(name='Administrator').first()

    # admin
    if User.query.filter_by(username='admin').first() is None:
        user = User(username='admin', fullname='admin', email='admin@test.com',
                    is_active=True, confirmed=True)
        user.password = 'admin123'
        user.role = admin
        db.session.add(admin)
    db.session.commit()

    # teachers
    for i in range(10):
        username = 't_%s' % i
        if User.query.filter_by(username=username).first() is None:
            user = User(username=username, fullname=username,
                        email='%s@test.com' % username,
                        is_active=True, confirmed=True)
            user.password = 'admin123'
            user.fullname = username
            user.role = teacher
            db.session.add(user)
    db.session.commit()

    # students
    for i in range(10):
        username = 's_%s' % i
        if User.query.filter_by(username=username).first() is None:
            user = User(username=username, fullname=username,
                        email='%s@test.com' % username,
                        is_active=True, confirmed=True)
            user.password = 'admin123'
            user.fullname = username
            user.role = student
            db.session.add(user)
    db.session.commit()


@manager.command
def test_param():
    from app.models import Parameter

    Parameter.insert_default_params()


@manager.command
def test(coverage=False):
    """Run the unit tests."""

    COV = None
    if True:
        import coverage
        COV = coverage.coverage(branch=True, include='app/*')
        COV.start()

    import unittest

    from tests import BasicsTestCase, CeleryTest, DesktopTest, ImageTest, \
        LogTest, NovaTest, SettingTest, StorageTest,EduTest
    # tests = unittest.TestLoader().discover('tests')
    tests = unittest.TestLoader().loadTestsFromTestCase(EduTest)
    unittest.TextTestRunner(verbosity=2).run(tests)

    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))

        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


@manager.command
def runserver():
    app.run(host='0.0.0.0', port=5000)


@manager.command
def run_vmotion():
    from app import vmotion_backend
    vmotion_backend.run()

if __name__ == '__main__':
    manager.run()
