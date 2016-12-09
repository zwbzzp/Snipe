# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/4/25 qinjinghui : Init
__author__ = 'qinjinghui'

#from pyDes import des, CBC, PAD_PKCS5
from Crypto.Cipher import AES
from binascii import hexlify, unhexlify


BS = AES.block_size
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]


#7uR3MaCl
def aes_initialization():
    #return des("DESCRYPT", CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
    return AES.new('UX6ROTTSxUfT1VMW', AES.MODE_CBC, 'GWHPWtxmIxHPkq8V')


def aes_encrypt(data):
    aes_obj = aes_initialization()
    encry_data = aes_obj.encrypt(pad(data))
    print(hexlify(encry_data).decode())
    #将二进制数据转化为十六进制数据来保存
    return hexlify(encry_data).decode()


def aes_decrypt(data):
    aes_obj = aes_initialization()
    #将十六进制数据转化为二进制数据再进行解密
    #decry_data = des_obj.decrypt(unhexlify(data), padmode=PAD_PKCS5)
    decry_data = aes_obj.decrypt(unhexlify(data))
    print(unpad(decry_data.decode()))
    return unpad(decry_data.decode())


def encrypt(data):
    aes = aes_encrypt(data)
    return aes


def decrypt(data):
    aes = aes_decrypt(data)
    return aes