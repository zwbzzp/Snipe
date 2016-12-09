#!/usr/bin/env python
#coding=utf-8
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "vinzoree.settings"

from module.account.models import User
from module.pool.vinzoree.pool.models import Desktop
from module.storage.vinzoree.storage.models import SambaServer, SambaAccount
from common.passwd import decrypt

# 创建目录
if not os.path.exists("db"):
    os.mkdir("db")

# 导出用户名单
user_list = User.objects.all()
user_header = ("#userid", "#email", "#is_superuser")
userid_len = len(user_header[0]) 
email_len = len(user_header[1])
issuper_len = len(user_header[2])
for user in user_list:
    if len(user.userid) > userid_len:
        userid_len = len(user.userid)
    if len(user.email) > email_len:
        email_len = len(user.email)
user_format = "%-" + str(userid_len) + "s %-" + str(email_len) + "s %-" + str(issuper_len) + "s"
with open("db/user.db", "w") as f:
    f.write(user_format % user_header)
    f.write(os.linesep)
    for user in user_list:
        f.write(user_format % (user.userid, user.email, user.is_superuser))
        f.write(os.linesep)

# 导出桌面列表
desktop_list = Desktop.objects.all()
desktop_header = ("#name", "#vmid", "#floating_ip", "#fixed_ip", "#vm_state", "#os_username", "#os_password", "#image", "#flavor", "#owner")
desktop_field_len = []
for field in desktop_header:
    desktop_field_len.append(len(field))
attrs = ("name", "vmid", "ip", "fixed_ip", "status", "username", "password", "templateid", "flavor", "owner")
for desktop in desktop_list:
    for index,attr in enumerate(attrs):
        if attr != "owner" and attr != "flavor" and attr != "password":
            attr_len = len(str(getattr(desktop, attr)))  
        elif attr == "flavor":
            attr_len = len(str(desktop.workgroup.flavor_id))
        elif attr == "owner":
            attr_len = len(str(desktop.owner.userid))
        elif attr == "password":
            attr_len = len(str(decrypt(desktop.password)))
        if attr_len > desktop_field_len[index]:
                desktop_field_len[index] = attr_len
desktop_format = []
for field_len in desktop_field_len:
    desktop_format.append("%-" + str(field_len) + "s")
desktop_format = " ".join(desktop_format)
with open("db/desktop.db", "w") as f:
    f.write(desktop_format % desktop_header)
    f.write(os.linesep)
    for desktop in desktop_list:
        f.write(desktop_format % (desktop.name, desktop.vmid, desktop.ip, desktop.fixed_ip, desktop.status, desktop.username,
                                  decrypt(desktop.password), desktop.templateid, desktop.workgroup.flavor_id, desktop.owner.userid))
        f.write(os.linesep)

