# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-12 qinjinghui : Init


from collections import namedtuple
from functools import partial

from flask.ext.principal import Permission, RoleNeed, TypeNeed

##################
# login user has permissions regarding below role type

# role permissions
admin_permission = Permission(RoleNeed('Administrator'))
user_permission = Permission(RoleNeed('User'))
bot_permission = Permission(RoleNeed('Bot'))

##################
# if login user can operate on below type of objects

# user type permission
UserTypeNeed = partial(TypeNeed, 'user')
user_type_perm = Permission(UserTypeNeed())

# Admin type permission
AdminTypeNeed = partial(TypeNeed, 'admin')
admin_type_perm = Permission(AdminTypeNeed())

# bot type permission
BotTypeNeed = partial(TypeNeed, 'bot')
bot_type_perm = Permission(BotTypeNeed())