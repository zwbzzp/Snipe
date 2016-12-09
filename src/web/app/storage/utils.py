# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/22 qinjinghui : Init
__author__ = 'qinjinghui'

import logging
import ftplib
import urllib
from random import randint, choice
import string
import json
import http.cookiejar

from .. import db
from .. import app
from ..models import SambaAccount, SambaServer, User, FtpAccount, FtpServer
from .forms import AddSambaAccountForm
from wtforms.validators import NumberRange

PERSONAL_ACCOUNT_MANAGE_PORT = 10087
LOG = logging.getLogger(__name__)


def check_ftp_login(host, port, username, password):
    ftp = None
    try:
        #check if current ftp server can login
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=5)
        ftp.login(username, password)
        if ftp:
            ftp.quit()
            return True
    except Exception as e:
        #ensure ftp is closed
        if ftp:
            ftp.quit()
        LOG.exception(e)
    return False


def generate_random_passwd():
    PASSWD_SEED = string.digits + string.ascii_letters
    passwd_len = randint(16, 20)
    passwd = []
    while len(passwd) < passwd_len:
        passwd.append(choice(PASSWD_SEED))
    return ''.join(passwd)


def isquota_format(quota):
    is_valid = False
    reason = None # when the quota is invalid, tell the reason

    # FIXME: we assume that the quota may be int, float and str
    if type(quota) == str:
        if quota == "":
            reason = "空间大小不能为空"
        elif not quota.isdigit():
            try:
                quota = float(quota)
            except Exception as ValueError:
                reason = "空间大小只能为整数"
            else:
                floor = int(quota)
                if quota - floor != 0:
                    reason = "空间大小只能为整数"
                else:
                    quota = floor
        else:
            quota = int(quota)
    elif type(quota) == float:
        # for example, 12.5 is invalid, 12.0 is valid
        # when we input a integer in the xls, it may be translated into float
        floor = int(quota)
        if quota - floor != 0:
            reason = "空间大小只能为整数"
        else:
            quota = floor

    # when the quota is invalid, return, no need to verify size
    if reason:
        return is_valid, reason

    # verify size
    # when the range of quota in the form AddSambaAccountForm changes, here no need to change
    quota_min = quota_max = None
    try:
        for validator in AddSambaAccountForm().quota.validators:
            if type(validator) == NumberRange:
                quota_min = getattr(validator, "min", None)
                quota_max = getattr(validator, "max", None)
                break
    except Exception as ex:
        LOG.exception(ex)

    if (quota_min and quota_min > quota) or (quota_max and quota_max < quota):
        reason = "空间大小的范围区间为[%s, %s]" % (quota_min or 1, quota_max or ">")
    else:
        is_valid = True

    return is_valid, reason
 

def judge_file(file, size):
    '''
    To judge whether the file is valid.
    @param file: the file object
    @param size: the size(MB) of the limit of the file.
    '''
    try:
        if file and size:
            if file.content_length > (size * 1024 * 1024):
                return False, "too large"
            temp = file.filename.split(".")
            file_type = temp[len(temp) - 1]
            if file_type == "xls" or file_type == "xlsx":
                return True, ""
            else:
                return False,"type error"
        else:
            raise "Invalid parameter"
    except Exception as ex:
        LOG.exception("Check File Failed")
        return False, ""


class StorageAccountManager(object):
    def __init__(self, host, user, passwd):
        self.__port = str(PERSONAL_ACCOUNT_MANAGE_PORT)
        self.__host = "http://" + host + ":" + self.__port
        self.__user = user
        self.__passwd = passwd
        self.__csrftoken = ""
        self.__cookie = http.cookiejar.CookieJar()
        cjhdr = urllib.request.HTTPCookieProcessor(self.__cookie)
        self.__opener = urllib.request.build_opener(cjhdr)

    def __do_post(self, url, postdata):
        postdata["csrfmiddlewaretoken"] = self.__csrftoken
        postdata = urllib.parse.urlencode(postdata)
        postdata = postdata.encode('utf-8')
        response = self.__opener.open(url, postdata)
        result = response.read().decode("utf-8")
        response.close()
        if result == "success":
            return True
        else:
            return False

    def login(self):
        url = self.__host + "/admin/"
        self.__opener.open(url)
        self.__csrftoken = ""
        for item in self.__cookie:
            if(item.name == 'csrftoken'):
                self.__csrftoken = item.value

        login_url = self.__host + "/login/"
        postdata = {'username': self.__user, 'password': self.__passwd}
        return self.__do_post(login_url, postdata)

    def logout(self):
        url = self.__host + "/admin/logout/"
        self.__opener.open(url)
        self.__opener.close()

    def add(self, userid, passwd, quota):
        url = self.__host + "/account/add/"
        postdata = {'userid': userid,
                    'password': passwd,
                    "quota": quota}
        return self.__do_post(url, postdata)

    def add_batch(self, accounts):
        """
        @param accounts: it must be a list type, each item is a tuple type.
            for example: [('account1', 'password1', '10G'), ('account2', 'password2', '10G')]
        """
        url = self.__host + "/account/add_batch/"
        postdata = {'accounts': json.dumps(accounts)}
        return self.__do_post(url, postdata)

    def delete(self, userid):
        url = self.__host + "/account/delete/"
        postdata = {'userid': userid}
        return self.__do_post(url, postdata)

    def delete_batch(self, accounts):
        """
        @param accounts: it must be a list type, each item is a str type.
            for example: ['account1', 'account2']
        """
        url = self.__host + "/account/delete_batch/"
        postdata = {'accounts': json.dumps(accounts)}
        return self.__do_post(url, postdata)

    def update(self, userid, passwd, quota):
        url = self.__host + "/account/update/"
        postdata = {'userid': userid,
                    'password': passwd,
                    "quota": quota}
        return self.__do_post(url, postdata)


def add_account_batch(samba_account_map):
    with app.app_context():
        result = {"insert": 0, "fail_list": []}
        for (samba_server_id, samba_account_list) in samba_account_map.items():
            if not samba_account_list:
                continue

            samba_server = SambaServer.query.filter_by(id=samba_server_id).first()
            manager = StorageAccountManager(host=samba_server.ip,
                                                user=samba_server.administrator,
                                                passwd=samba_server.password)
            ret = False
            err_info = "数据保存失败"
            try:
                if manager.login():
                    if manager.add_batch(samba_account_list):
                        for account_info in samba_account_list:
                            user = User.query.filter_by(id=account_info[0]).first()
                            account = SambaAccount()
                            account.samba_server_id = samba_server_id
                            account.user_id = user.id
                            account.password = account_info[1]
                            account.quota = str(account_info[2])+'B'
                            db.session.add(account)
                            db.session.commit()
                        result['insert'] += len(samba_account_list)
                        ret = True
                    else:
                        err_info = "磁盘配额超过物理硬盘的总容量"
                    manager.logout()
            except Exception as ex:
                LOG.exception("%s", ex)
                err_info = "个人文件服务器连接失败"
            finally:
                if not ret:
                    for account_info in samba_account_list:
                        error = {'sambaip': samba_server.ip,
                                'userid': account_info[0],
                                'info': err_info}
                        result['fail_list'].append(error)
        return result


def check_ftp_using(ftp_id):
    ftp_list = FtpAccount.query.filter_by(ftp_server_id=ftp_id).all()
    if ftp_list:
        return True
    else:
        return False


def check_samba_using(samba_id):
    samba_list = SambaAccount.query.filter_by(samba_server_id=samba_id).all()
    if samba_list:
        return True
    else:
        return False