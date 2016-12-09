# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Image API
#
# 2016/1/23 lipeizhao: implementation

from phoenix.cloud import utils
from phoenix.cloud import CONF


_BACKEND_MAPPING = {'openstack': 'phoenix.cloud.openstack.image'}

IMPL = utils.CLOUDAPI.from_config(conf=CONF, backend_mapping=_BACKEND_MAPPING)


def get_image(image_id):
    """
    Get server by server ID.
    """
    return IMPL.get_image(image_id)


def get_image_by_name(name):
    """
    Get image by name.
    """
    return IMPL.get_image_by_name(name)


def list_images(**kwargs):
    """
    Retrieve a listing of Image objects.

    :param page_size: Number of images to request in each
                      paginated request.
    """
    return IMPL.list_images(**kwargs)


def get_image_date(image_id, do_checksum=True):
    """
    Retrieve data of an image.
    """
    return IMPL.get_image_date(image_id, do_checksum)


def upload_image(image_id, image_data):
    """
    Upload the data for an image.
    """
    return IMPL.upload_image(image_id, image_data)


def delete_image(image_id):
    """
    Delete an image.
    """
    return IMPL.delete_image(image_id)


def create_image(**kwargs):
    """
    Create an image.
    """
    return IMPL.create_image(**kwargs)


def deactivate_image(image_id):
    """
    Deactivate an image.
    """
    return IMPL.deactivate_image(image_id)


def reactivate_image(image_id):
    """
    Reactivate an image.
    """
    return IMPL.reactivate_image(image_id)


def update_image(image_id, remove_props=None, **kwargs):
    """
    Update attributes of an image.

    :param image_id: ID of the image to modify.
    :param remove_props: List of property names to remove
    :param \*\*kwargs: Image attribute names and their new values.
    """
    return IMPL.update_image(image_id, remove_props=None, **kwargs)


def get_image_metadata(image_id):
    """
    Retrive metadata of an image.
    """
    return IMPL.get_image_metadata(image_id)
