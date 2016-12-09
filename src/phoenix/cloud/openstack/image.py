# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Openstack API implementation
#
# 2016/1/25 lipeizhao: Init

import sys

from phoenix.cloud.openstack.client import ClientManager
from phoenix.cloud.utils import wrap_cloud_retry
from phoenix.common.proxy import SimpleProxy


def get_backend():
    """
    The backend is this module itself.
    """
    return sys.modules[__name__]

GLANCE_CLI = SimpleProxy(lambda: ClientManager().glance_client)

NOVA_CLI = SimpleProxy(lambda: ClientManager().nova_client)

# IMAGES = SimpleProxy(lambda: GLANCE_CLI.images)

###################


def get_image(image_id):
    """
    Get server by server ID.
    """
    return GLANCE_CLI.images.get(image_id)


def get_image_by_name(name):
    """
    Get image by name
    """
    generator = GLANCE_CLI.images.list(name=name)
    for img in generator:
        if img.name == name:
            return img
    return None


def list_images(**kwargs):
    """
    List all servers.
    """


    generator = GLANCE_CLI.images.list(**kwargs)
    images = []
    for img in generator:
        images.append(img)
    return images


def get_image_date(image_id, do_checksum=True):
    """
    Retrieve data of an image.
    """
    return GLANCE_CLI.images.data(image_id, do_checksum)


def upload_image(image_id, image_data):
    """
    Upload the data for an image.
    """
    return GLANCE_CLI.images.upload(image_id, image_data)


def delete_image(image_id):
    """
    Delete an image.
    """
    return GLANCE_CLI.images.delete(image_id)


def create_image(**kwargs):
    """
    Create an image.
    """
    return GLANCE_CLI.images.create(**kwargs)


def deactivate_image(image_id):
    """
    Deactivate an image.
    """
    return GLANCE_CLI.images.deactivate(image_id)


def reactivate_image(image_id):
    """
    Reactivate an image.
    """
    return GLANCE_CLI.images.reactivate(image_id)


def update_image(image_id, remove_props=None, **kwargs):
    """
    Update attributes of an image.

    :param image_id: ID of the image to modify.
    :param remove_props: List of property names to remove
    :param \*\*kwargs: Image attribute names and their new values.
    """
    return GLANCE_CLI.images.update(image_id, remove_props, **kwargs)


def get_image_metadata(image_id):
    """
    Retrieve metadata of an image.
    """
    return NOVA_CLI.images.get(image_id).metadata
