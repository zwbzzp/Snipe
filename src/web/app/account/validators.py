from sqlalchemy import and_

from ..models import User
from .. import db


class ValidationError(ValueError):
    """
    Raised when a validator fails to validate its input.
    """
    def __init__(self, message='', *args, **kwargs):
        ValueError.__init__(self, message, *args, **kwargs)


class AccountUnique(object):
    """
    Validates if the Account is unique.

    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        username = field.data
        user = User.query.filter_by(username = username).first()
        if user:
            raise ValidationError('用户名已经存在')


class EmailUnique(object):
    """
    Validates if the email is unique.

    :param username:
        The account id of the user that email will modified.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, username_field_name=None, message=None):
        self.username_field_name = username_field_name
        self.message = message

    def __call__(self, form, field):
        email = field.data
        try:
            username = form[self.username_field_name].data
        except KeyError:
            username = None
        count_with_same_email = User.query.filter(and_(User.username != username,
                                                       User.email == email)).count()
        if count_with_same_email >= 1:
            raise ValidationError('邮件地址已被使用')
