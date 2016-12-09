import os, sys, re
import datetime
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
from app.models import User, Role, Desktop, DesktopState

# check db
if not os.path.exists("db"):
    raise Exception("Cannot find db directory!")

def import_user():
    print("##########导入用户##########")
    stundet_role = Role.query.filter_by(name="Student").first()
    admin_role = Role.query.filter_by(name="Administrator").first()
    with open("db/user.db", "r") as f:
        f.readline()
        for line in f.readlines():
            line = line.strip('\n').split()
            user = User.query.filter_by(username=line[0]).first()
            if user is None:
                user = User(username=line[0], fullname=line[0], email=line[1], password="admin123", confirmed=True)
                if line[-1] == str(True):
                    user.role = admin_role
                else:
                    user.role = stundet_role
                db.session.add(user)
                db.session.commit()
                print(user)
            else:
                print("%s已经存在" % line[0])
    print()

def import_desktop():
    print("##########导入桌面##########")
    with open("db/desktop.db", "r") as f:
        f.readline()
        for line in f.readlines():
            line = line.strip('\n').split()
            name, vm_ref, floating_ip, fixed_ip, vm_state, username = line[0], line[1], line[2], line[3], line[4], line[-1]
            desktop = Desktop.query.filter_by(vm_ref=vm_ref).first()
            if desktop is None:
                owner = User.query.filter_by(username=username).first()
                desktop = Desktop(name=name, vm_ref=vm_ref, vm_state="ACTIVE", desktop_state="ACTIVE", desktop_type="STATIC",
                                  floating_ip=floating_ip, fixed_ip=fixed_ip, owner=owner, need_floating=False, 
                                  start_datetime=datetime.datetime.now(), end_datetime=datetime.datetime(3016, 1, 1, 0, 0, 0, 1))
                db.session.add(desktop)
                db.session.commit()
                print(desktop)
            else:
                print("%s已经存在" % vm_ref)
                
with app.app_context():
    import_user()
    import_desktop()
