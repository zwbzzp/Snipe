# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 16-7-13 qinjinghui : Init


import datetime
import subprocess
import os
import rsa
from random import randint, choice
import string
import hashlib
from binascii import hexlify,unhexlify

import requests
import shutil


class LicenseUtils():
    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.join(basedir, '../static/')
    private_key_pem_path = os.path.join(basedir,
                                        'license_key/instance_private.pem')
    public_key_pem_path = os.path.join(basedir,
                                       'license_key/instance_public.pem')
    vinzor_pubkey_pem_path = os.path.join(basedir,
                                          'license_key/vinzor_public.pem')
    host_info_file_path = os.path.join(basedir, 'hostinfo.dat')
    license_file_path = os.path.join(basedir,'license_key/license.dat')
    temp_license_file_path = os.path.join(basedir,
                                          'license_key/temp_license.dat')

    def __init__(self):
        pass

    def _generate_serial_number(self):
        SN_SEED = string.digits + string.ascii_letters
        sn_len = randint(16, 20)
        sn = []
        while len(sn) < sn_len:
            sn.append(choice(SN_SEED))
        return ''.join(sn)

    def get_mac_address(self):
        mac_address = ""
        try:
            get_default_interface = "route -n | grep 0.0.0.0 | grep UG"
            get_default_interface_process = subprocess.Popen(
                get_default_interface,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True, )
            get_default_interface_out, get_default_interface_err = \
                get_default_interface_process.communicate()
            get_default_interface_out = get_default_interface_out.decode()
            get_default_interface_out = get_default_interface_out.split()
            default_interface = get_default_interface_out[7]

            get_mac_address = "ifconfig | grep 'HWaddr' | grep %s" % \
                         default_interface
            get_mac_address_process = subprocess.Popen(get_mac_address,
                                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, shell=True, )
            get_mac_address_out, get_mac_address_err = \
                get_mac_address_process.communicate()
            get_mac_address_out = get_mac_address_out.decode()
            get_mac_address_out = get_mac_address_out.split()
            mac_address = get_mac_address_out[4]
        except Exception as ex:
            return "00:00:00:00:00:00"
        return mac_address

    def get_serial_number(self):
        serial_number = ""
        try:
            get_ssn_cmd = "dmidecode -s system-serial-number | grep -v '#'"
            p = subprocess.Popen(get_ssn_cmd, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, shell=True, )
            out, err = p.communicate()
            serial_number = out.decode()
            if serial_number.find('Not Specified') == 0 or serial_number.find(
                    'None') == 0 or serial_number.find('To be filled by '
                                                       'O.E.M.') == 0 or \
                serial_number.find('O.E.M.') == 0:
                get_bsn_cmd = "dmidecode -s baseboard-serial-number | grep -v '#'"
                p = subprocess.Popen(get_bsn_cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=True, )
                out, err = p.communicate()
                out = out.decode()
                serial_number = out.split()
                if serial_number.find('Not Specified') == 0 or \
                        serial_number.find('None') == 0 \
                        or serial_number.find('To be filled by O.E.M.') == 0 \
                        or serial_number.find('O.E.M.') == 0:
                    serial_number = self._generate_serial_number()
        except Exception as ex:
            serial_number = self._generate_serial_number()
        return serial_number.strip()

    def generate_host_info(self, instanceid="sysu"):

        if not os.path.exists(self.vinzor_pubkey_pem_path):
            return ("No Vinzor Public Key","","")

        #if os.path.exists(self.host_info_file_path):
        #    return ("Host Info File Existed","","")

        if not os.path.exists(self.public_key_pem_path) or not os.path.exists(
                self.private_key_pem_path):
            (pubkey, prikey) = rsa.newkeys(1024)
            pri = prikey.save_pkcs1()
            prifile = open(self.private_key_pem_path, 'w+')
            prifile.write(pri.decode())
            prifile.close()

            pub = pubkey.save_pkcs1()
            pubfile = open(self.public_key_pem_path, 'w+')
            pubfile.write(pub.decode())
            pubfile.close()

        vinzor_pubkey_file = open(self.vinzor_pubkey_pem_path,"rb")
        vinzor_pubkey_data = vinzor_pubkey_file.read()
        vinzor_pubkey = rsa.PublicKey.load_pkcs1(vinzor_pubkey_data)
        vinzor_pubkey_file.close()


        mac = self.get_mac_address()
        sn = self.get_serial_number()
        md5 = hashlib.md5()
        md5.update(sn.encode())
        psw = md5.hexdigest()[:64]

        ciphertext = rsa.encrypt(psw.encode(), vinzor_pubkey)
        ciphertext = hexlify(ciphertext).decode()

        host_info_file = open( self.host_info_file_path,"w+")
        host_info_file.write(instanceid + '\n')
        host_info_file.write(mac+'\n')
        host_info_file.write(sn+'\n')
        host_info_file.write(ciphertext+'\n')
        with open(self.public_key_pem_path, 'r') as f:
            pub = rsa.PublicKey.load_pkcs1(f.read().encode())
        host_info_file.write(pub.save_pkcs1().decode())
        host_info_file.close()

        return ("success", mac, sn)

    def save_temp_license_file(self, upload_file):
        license_file = open(self.temp_license_file_path,"w+")
        license_file.close()
        upload_file.save(self.temp_license_file_path)

    def get_license_file_from_cache(self):
        if not os.path.exists(self.temp_license_file_path):
            return None
        try:
            license_file = open(self.temp_license_file_path, "rb")
            return license_file
        except:
            return None

    def save_license_data(self, license_data):
        license_file = open(self.license_file_path,"wb+")
        license_file.write(license_data)
        license_file.close()


    def get_license_info(self):
        if not os.path.exists(self.license_file_path):
            return (-1,-1,-1,-1,-1,-1,-1,'','')

        instance_prikey_file = open(self.private_key_pem_path,"rb")
        instance_prikey_data = instance_prikey_file.read()
        instance_prikey = rsa.PrivateKey.load_pkcs1(instance_prikey_data)
        instance_prikey_file.close()

        license_file =  open(self.license_file_path,"rb")
        license_data = license_file.read()
        decry_data = rsa.decrypt(unhexlify(license_data.strip().decode()),
                                 instance_prikey)
        raw_data = decry_data.decode()
        data = raw_data.split("\n")
        max_desktops = data[0]
        max_user = data[1]
        max_images  = data[2]
        max_vcpu  = data[3]
        max_vmem = data[4]
        max_vdisk = data[5]
        expired_time = data[6]
        mac = data[7]
        sn = data[8]

        # judge if date is expired
        if datetime.datetime.strptime(expired_time, "%Y-%m-%d") < datetime.datetime.now():
            return (-1,-1,-1,-1,-1,-1,-1,'','')

        return (max_desktops,max_user,max_images,max_vcpu, max_vmem,  max_vdisk, expired_time,mac,sn)

    def get_license_info_from_upload_file(self,license_file):
        self.save_temp_license_file(license_file)
        license_file = self.get_license_file_from_cache()
        instance_prikey_file = open(self.private_key_pem_path, "rb")
        instance_prikey_data = instance_prikey_file.read()
        instance_prikey = rsa.PrivateKey.load_pkcs1(instance_prikey_data)
        instance_prikey_file.close()

        license_data = license_file.read()
        decry_data = rsa.decrypt(unhexlify(license_data.strip().decode()),
                                 instance_prikey)
        raw_data = decry_data.decode()
        data = raw_data.split("\n")
        max_desktops = data[0]
        max_user = data[1]
        max_images = data[2]
        max_vcpu = data[3]
        max_vmem= data[4]
        max_vdisk= data[5]
        expired_time = data[6]
        mac = data[7]
        sn = data[8]
        self.save_license_data(license_data)
        return (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn)


    def check_max_desktops(self, current_desktops):
        if not os.path.exists(self.license_file_path):
            return True
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk,expired_time,mac,sn) = self.get_license_info()

        if int(max_desktops) < current_desktops:
            return True
        else:
            return False

    def check_max_images(self, current_images):
        if not os.path.exists(self.license_file_path):
            return True
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn) = self.get_license_info()

        if int(max_images) < current_images:
            return True
        else:
            return False

    def check_max_users(self, current_users):
        if not os.path.exists(self.license_file_path):
            return True
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn) = self.get_license_info()

        if int(max_user) < current_users:
            return True
        else:
            return False

    def check_max_vcpu(self, current_vcpu):
        if not os.path.exists(self.license_file_path):
            return True
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn) = self.get_license_info()

        if int(max_vcpu) < current_vcpu:
            return True
        else:
            return False

    def check_max_vmem(self, current_vmem):
        if not os.path.exists(self.license_file_path):
            return True
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk,expired_time,mac,sn) = self.get_license_info()

        if int(max_vmem) < current_vmem:
            return True
        else:
            return False

    def check_max_vdisk(self, current_vdisk):
        if not os.path.exists(self.license_file_path):
            return True
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn) = self.get_license_info()

        if int(max_vdisk) < current_vdisk:
            return True
        else:
            return False


    def check_expired_time(self, current_time):
        if not os.path.exists(self.license_file_path):
            return True
        (max_desktops, max_user, max_images, max_vcpu, max_vmem, max_vdisk, expired_time,mac,sn) = self.get_license_info()

        if datetime.datetime.strptime(expired_time, "%Y-%m-%d") < current_time:
            return True
        else:
            return False

    def download_license_file(self,license_url="", instanceid="sysu"):
        try:
            s = requests.Session()
            res = s.get(license_url)
            if res.status_code != 200:
                return False
            result = res.content.decode().split(" ")
            i = 0;
            resultLen = len(result)
            while i < resultLen:
                if result[i] == 'id="csrf_token"':
                    if i + 1 < resultLen and result[
                                i + 1] == 'name="csrf_token"':
                        csrf_token = result[i + 3]
                        break
                i = i + 1
            csrf_token = csrf_token.split('"')[1]
            data = {'username_email': 'anonymousrobot',
                    'password': 'dacvrwomby',
                    "csrf_token": csrf_token}

            s.headers["X-CSRFToken"] = csrf_token

            res = s.post(license_url+'/account/login', data=data)
            if res.status_code != 200:
                return False

            data = {"csrf_token": csrf_token, 'instanceid': instanceid}
            res = s.post(license_url+'/instance/download_license', data=data)
            if res.status_code != 200:
                return False

            res = s.get(license_url + '/static/license/' + instanceid.upper()+'_LICENSE',
                        stream=True)
            if res.status_code != 200:
                return False
            # with open(self.license_file_path, 'w+') as f:
            #     f.write(res.raw.read().decode())
            with open(self.license_file_path, 'wb') as f:
                res.raw.decode_content = True
                shutil.copyfileobj(res.raw, f)
            return True
        except:
            return False

    def upload_hostinfo(self,license_url="", instanceid="sysu"):
        try:
            s = requests.Session()
            res = s.get(license_url)
            if res.status_code != 200:
                return False
            result = res.content.decode().split(" ")
            i = 0;
            resultLen = len(result)
            while i < resultLen:
                if result[i] == 'id="csrf_token"':
                    if i + 1 < resultLen and result[
                                i + 1] == 'name="csrf_token"':
                        csrf_token = result[i + 3]
                        break
                i = i + 1
            csrf_token = csrf_token.split('"')[1]
            data = {'username_email': 'anonymousrobot',
                    'password': 'dacvrwomby',
                    "csrf_token": csrf_token}

            s.headers["X-CSRFToken"] = csrf_token
            res = s.post(license_url + '/account/login', data=data)
            if res.status_code != 200:
                return False

            files = {'file': open(self.host_info_file_path, 'rb')}
            data = {"csrf_token": csrf_token, 'instanceid': instanceid}
            res = s.post(license_url + '/instance/upload_hostinfo',
                         files=files, data=data)
            if res.status_code != 200:
                return False
            return True
        except:
            return False

    def download_license_file_from_django_app(self,license_url="",
                                         instanceid="sysu"):
        try:
            s = requests.Session()
            res = s.get(license_url)
            if res.status_code != 200:
                return False

            token = s.cookies["csrftoken"]
            data = {'csrfmiddlewaretoken': token, 'userid': 'anonymousrobot', 'password':
                'dacvrwomby'}
            res = s.post(license_url+'/account/login_result/', data=data)
            if res.status_code != 200:
                return False

            data = {'csrfmiddlewaretoken': token, 'instanceid': instanceid}
            res = s.post(license_url+'/instance/downloadLicense/', data=data)
            if res.status_code != 200:
                return False

            res = s.get(license_url + '/download/' + instanceid.upper()+'_LICENSE',
                        stream=True)
            if res.status_code != 200:
                return False
            # with open(self.license_file_path, 'w+') as f:
            #     f.write(res.raw.read().decode())
            with open(self.license_file_path, 'wb') as f:
                res.raw.decode_content = True
                shutil.copyfileobj(res.raw, f)
            return True
        except:
            return False

    def upload_hostinfo_to_django_app(self,license_url="", instanceid="sysu"):
        try:
            s = requests.Session()
            res = s.get(license_url)
            if res.status_code != 200:
                return False

            token = s.cookies["csrftoken"]
            data = {'csrfmiddlewaretoken': token, 'userid': 'anonymousrobot',
                    'password': 'dacvrwomby'}
            res = s.post(license_url + '/account/login_result/', data=data)
            if res.status_code != 200:
                return False

            files = {'file': open(self.host_info_file_path, 'rb')}
            data = {'csrfmiddlewaretoken': token, 'instanceid': instanceid}
            res = s.post(license_url + '/instance/uplodadHostinfo/',
                         files=files, data=data)
            if res.status_code != 200:
                return False
            return True
        except:
            return False




if __name__ == '__main__':
    import json
    license_url="http://172.168.215.4:8001"
    license_file_path = "/home/scape/test_license"
    s = requests.Session()
    res = s.get(license_url)
    #token = s.cookies["csrftoken"]
    result = res.content.decode().split(" ")

    i = 0;
    resultLen = len(result)
    while i < resultLen:
        if result[i] == 'id="csrf_token"':
            if i + 1 < resultLen and result[i+1] == 'name="csrf_token"':
                csrf_token = result[i+3]
                break
        i = i+1
    csrf_token = csrf_token.split('"')[1]
    data = {'username_email': 'anonymousrobot',
            'password': 'dacvrwomby',
            "csrf_token":csrf_token}
    s.headers["X-CSRFToken"]= csrf_token
    res = s.post(license_url + '/account/login', data=data)
    print(res.content)

    data = {"csrf_token":csrf_token, 'instanceid': "test"}
    res = s.post(license_url + '/instance/download_license', data=data)


    res = s.get(license_url + '/static/license/' + "test".upper() + '_LICENSE',
                stream=True)

    # with open(self.license_file_path, 'w+') as f:
    #     f.write(res.raw.read().decode())
    with open(license_file_path, 'wb') as f:
        res.raw.decode_content = True
        shutil.copyfileobj(res.raw, f)

    #data = {'csrfmiddlewaretoken': token, 'instanceid': 'test'}
    # res = s.post(license_url + '/instance/downloadLicense/', data=data)
    #
    #
    # res = s.get(
    #     license_url + '/download/' + 'test'.upper() + '_LICENSE',
    #     stream=True)



    # import requests
    # import shutil
    # s = requests.Session()
    # res = s.get('http://172.168.215.4:8000');
    # token = s.cookies["csrftoken"]
    # print(token)
    # data = {'csrfmiddlewaretoken': token, 'userid': 'admin', 'password':
    #     'admin123'}
    # res = s.post('http://172.168.215.4:8000/account/login_result/',data=data)
    # print(res)
    # print(res.text)
    #
    # basedir = os.path.abspath(os.path.dirname(__file__))
    # basedir = os.path.join(basedir, '../static/')
    # host_info_file_path = os.path.join(basedir, 'hostinfo')
    # files = {'file':open(host_info_file_path,'rb')}
    # data={'csrfmiddlewaretoken': token, 'instanceid': 'sysu'}
    # res = s.post('http://172.168.215.4:8000/instance/uplodadHostinfo/',
    #              files=files,data=data)
    # print(res.text)
    #
    # data = {'csrfmiddlewaretoken': token, 'instanceid':'sysu'}
    # res = s.post('http://172.168.215.4:8000/instance/downloadLicense/',
    #              data=data)
    # print(res)
    #
    # res = s.get('http://172.168.215.4:8000/download/SYSU_LICENSE', stream=True)
    # with open("./test.txt", 'w+') as f:
    #     f.write(res.raw.read().decode())



    # with open("./test.txt", 'wb') as f:
    #     res.raw.decode_content = True
    #     shutil.copyfileobj(res.raw, f)
    # print(res)

    # license_utils = LicenseUtils()
    # print(license_utils.get_mac_address())
    # print(license_utils.get_serial_number())
    # print(license_utils.generate_host_info())

    # basedir = os.path.abspath(os.path.dirname(__file__))
    # basedir = os.path.join(basedir, '../static/')
    # private_key_pem_path = os.path.join(basedir,
    #                                     'license_key/instance_private.pem')
    # public_key_pem_path = os.path.join(basedir,
    #                                    'license_key/instance_public.pem')
    # vinzor_pubkey_pem_path = os.path.join(basedir,
    #                                       'license_key/vinzor_public.pem')
    # vinzor_prikey_pem_path = os.path.join(basedir,
    #                                       'license_key/vinzor_private.pem')
    #
    # vinzor_pubkey_file = open(vinzor_pubkey_pem_path, "r")
    # vinzor_pubkey_data = vinzor_pubkey_file.read().encode()
    # vinzor_pubkey = rsa.PublicKey.load_pkcs1(vinzor_pubkey_data)
    # vinzor_pubkey_file.close()
    #
    # ciphertext = rsa.encrypt("VMware-56 4d 69 c0 49 af d2 f4-b6 23 2e 98 0c d2 94 42".encode(), vinzor_pubkey)
    # ciphertext = hexlify(ciphertext).decode()
    # print(ciphertext)
    #
    # vinzor_prikey_file = open(vinzor_prikey_pem_path, "r")
    # vinzor_prikey_data = vinzor_prikey_file.read().encode()
    # vinzor_prikey = rsa.PrivateKey.load_pkcs1(vinzor_prikey_data)
    # vinzor_prikey_file.close()
    #
    # text = rsa.decrypt(unhexlify(ciphertext), vinzor_prikey).decode()
    # print(vinzor_prikey)
    # print(text)