# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Context for requests that persist through
#
# 2016/1/22 fengyc : Init


class Context(object):
    """ Security context and request information
    """
    def __init__(self, user_id, **kwargs):
        """ Init context
        :param user_id: user id
        :param kwargs: extra p
        :return:
        """
        self.user_id = user_id
