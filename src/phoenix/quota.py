# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Quota
#
# 2016/1/22 fengyc : Init


def get_instances_quota(context, user_id, default=True):
    """ Get instance quota
    :param context:
    :param user_id:
    :param default:
    :return:
    """
    raise NotImplementedError


def get_vcpu_quota(context, user_id, default=True):
    """ Get vcpu quota
    :param context:
    :param user_id:
    :param default:
    :return:
    """
    raise NotImplementedError


def get_storage_quota(context, user_id, default=True):
    """ Get storage quota
    :param context:
    :param user_id:
    :param default:
    :return:
    """
    raise NotImplementedError


def get_network_quota(context, user_id, default=True):
    """ Get network quota
    :param context:
    :param user_id:
    :param default:
    :return:
    """


def get_firewall_quota(context, user_id, default=True):
    """ Get firewall quota
    :param context:
    :param user_id:
    :param default:
    :return:
    """
    raise NotImplementedError