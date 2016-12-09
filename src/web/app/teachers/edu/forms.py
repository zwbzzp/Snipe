# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 2016/2/18 fengyc : Init

import datetime
from ... import db
from flask.ext.wtf import Form
from flask.ext.login import current_user

from wtforms import Field, StringField, SubmitField, FieldList, FormField,\
    DateField, IntegerField, SelectField, SelectMultipleField, DateTimeField, \
    FileField, RadioField, ValidationError

from wtforms.validators import data_required, length, regexp, number_range, optional
from phoenix.cloud import image as OpenstackImageService
from phoenix.cloud import compute as OpenstackComputeService
from phoenix.cloud import network as OpenstackNetworkService
from ...models import Period, Image, User
from ...jinja_filters import time_format
from ...common import imageutils

def choice_of_teachers():
    from ...models import Role, User
    query = User.query.outerjoin(User.role).filter(Role.name == 'Teacher')
    teachers = query.all()
    return [(teacher.id, teacher.fullname) for teacher in teachers]

def choice_of_students():
    from ...models import Role, User
    query = User.query.outerjoin(User.role).filter(Role.name == 'Teacher')
    teachers = query.all()
    return [(teacher.id, teacher.fullname) for teacher in teachers]

def choices_of_images():
    return [(i.id, i.name) for i in imageutils.list_of_image()]


def choices_of_flavors():
    return [(i.id, "%s - %sVCPU|%sMB|%sGB" % (i.name, i.vcpus, i.ram, i.disk)) for i in OpenstackComputeService.list_flavors()]


def choices_of_networks():
    networks = OpenstackNetworkService.list_networks()
    choices = []
    try:
        choices = [(i["id"], i["name"]) for i in networks.get("networks") if not i["router:external"]]
    except:
        # nova
        choices = [(i.id, i.label) for i in networks]
    return choices


def choice_of_weekdays():
    return [(0, '星期一'),
            (1, '星期二'),
            (2, '星期三'),
            (3, '星期四'),
            (4, '星期五'),
            (5, '星期六'),
            (6, '星期天')]

def choice_of_period():
    from ... import db
    from ...models import Period
    periods = Period.query.order_by(db.asc(Period.start_time)).all()
    return [(period.id, "第%s节 %s-%s" % (period.name, time_format(period.start_time), time_format(period.end_time))) for period in periods]

def choice_of_place():
    from ...models import Place
    places = Place.query.all()
    return [(place.id, place.name) for place in places]

def choice_of_protocol():
    from ...models import Protocol
    protocols = Protocol.query.all()
    return [(protocol.id, protocol.name) for protocol in protocols]

def default_of_protocol():
    from ...models import Parameter, Protocol
    default_protocol_name = Parameter.query.filter_by(name='default_protocol').first().value
    if default_protocol_name is None:
        return 1
    result = Protocol.query.filter_by(name = default_protocol_name).first().id
    return result

class CourseForm(Form):
    name = StringField('课程名称', validators=[data_required(), length(1, 64)])
    # owner_id = SelectField('Owner', choices=[], coerce=int)
    owner_id = IntegerField('授课老师', validators=[data_required()])
    start_date = DateField('开始日期', validators=[data_required()], format='%Y-%m-%d')
    end_date = DateField('结束日期', validators=[data_required()], format='%Y-%m-%d')
    capacity = IntegerField('桌面数量', default=0)
    image_ref = SelectField('课程镜像', validators=[data_required()], choices=[])
    flavor_ref = SelectField('桌面类型', validators=[data_required()], choices=[])
    network_ref = SelectField('虚拟内网', choices=[], default=None)
    places = SelectMultipleField('指定教室', choices=[], coerce=int)
    protocol = SelectField('客户端连接协议', validators=[data_required()], coerce=int, choices=[])

    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)
        # self.owner_id.choices = choice_of_teachers()  # 此处ajax加载
        self.image_ref.choices = choices_of_images()
        self.flavor_ref.choices = choices_of_flavors()
        self.places.choices = choice_of_place()
        self.network_ref.choices = choices_of_networks()
        self.protocol.choices = choice_of_protocol()
        self.protocol.default = default_of_protocol()

    def validate_start_date(self, field):
        if self.start_date.data > self.end_date.data:
            raise ValidationError('开始日期必须小于结束日期')

    def validate_end_date(self, field):
        if self.start_date.data > self.end_date.data:
            raise ValidationError('开始日期必须小于结束日期')

    def validate_capacity(self, field):
        if self.capacity.data < 0:
            raise ValidationError('必须为不小于0的整数')

    class Meta:
        locales = ['zh','cn']

#################
# student form
class UploadStudentFileForm(Form):
    file = FileField('File', validators=[data_required()])

class StudentListForm(Form):
    students = StringField('学生列表', validators=[data_required(), regexp(r"([0-9]+[,]?)+", message="非法数据")])

#################
# lesson forms
# support weekly, daily or oneday
# support timetable or customize

class OnedayLessonFormMixin(object):
    start_date = DateField('开始日期', format='%Y-%m-%d', validators=[optional()])
    end_date = DateField('结束日期', format='%Y-%m-%d', validators=[optional()])


class WeeklyLessonFormMixin(object):
    start_weekday = SelectField('开始日期', choices=choice_of_weekdays(),
                                coerce=int, validators=[number_range(0, 7), optional()])
    end_weekday = SelectField('结束日期', choices=choice_of_weekdays(),
                              coerce=int, validators=[number_range(0, 7), optional()])


class PeriodLessonFormMixin(object):
    start_period_id = SelectField('开始节数', choices=[], coerce=int, validators=[optional()])
    end_period_id = SelectField('结束节数', choices=[], coerce=int, validators=[optional()])

    def validate_start_period_id(self, field):
        pass

    def validate_end_period_id(self, field):
        pass


class CustomizedLessonFormMixin(object):
    start_time = DateTimeField('开始时间', format='%H:%M', validators=[optional()])
    end_time = DateTimeField('结束时间', format='%H:%M', validators=[optional()])


class DailyWithPeriodLessonForm(Form, PeriodLessonFormMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_period_id.choices = choice_of_period()
        self.end_period_id.choices = choice_of_period()

class DailyWithCustomizedLessonForm(Form, CustomizedLessonFormMixin):
    pass

class WeeklyWithPeriodLessonForm(Form, WeeklyLessonFormMixin, PeriodLessonFormMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_period_id.choices = choice_of_period()
        self.end_period_id.choices = choice_of_period()

class WeeklyWithCustomizedLessonForm(Form, WeeklyLessonFormMixin, CustomizedLessonFormMixin):
    pass

class OnedayWithPeriodLessonForm(Form, OnedayLessonFormMixin, PeriodLessonFormMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_period_id.choices = choice_of_period()
        self.end_period_id.choices = choice_of_period()


class OnedayWithCustomizedLessonForm(Form, OnedayLessonFormMixin, CustomizedLessonFormMixin):
    pass

class CustomizedLessonForm(Form):
    # TODO Need iso8601 format
    start_datetime = DateTimeField('Start Date & Time', validators=[data_required()])
    end_datetime = DateTimeField('End Date & Time', validators=[data_required()])


class LessonForm(Form, OnedayLessonFormMixin, WeeklyLessonFormMixin, PeriodLessonFormMixin, CustomizedLessonFormMixin):

    @staticmethod
    def choice_of_frequency():
        return [("weekly", "每周"),
                ("daily", "每天"),
                ("once", "单次")]

    @staticmethod
    def choice_of_timetype():
        return [("period", "按节数"),
                ("customized", "按时间点")]

    frequency = RadioField('选择频率', choices=choice_of_frequency.__func__(), validators=[data_required()])
    start_time_type = RadioField('开始时间', choices=choice_of_timetype.__func__(), validators=[data_required()])
    end_time_type = RadioField('结束时间', choices=choice_of_timetype.__func__(), validators=[data_required()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_period_id.choices = choice_of_period()
        self.end_period_id.choices = choice_of_period()

    def validate_end_weekday(self, field):
        if self.frequency.data == "weekly":
            if self.start_weekday.data > self.end_weekday.data:
                raise ValidationError("结束日期不能小于开始日期")

    def validate_end_date(self, field):
        if self.frequency.data == "once":
            if self.start_date.data > self.end_date.data:
                raise ValidationError("结束日期不能小于开始日期")


class TempLessonForm(Form):
    """ Temporary lesson

    A temporary lesson starts from now, and ends at specific date and time.
    """
    end_date = DateField(format='%Y-%m-%d')
    end_time_type = RadioField(choices=[], validators=[data_required()])
    end_period_id = SelectField(choices=[], coerce=int)
    end_time = DateTimeField(format='%H:%M')

    def __init__(self, *args, **kwargs):
        super(TempLessonForm, self).__init__(*args, **kwargs)
        self.end_period_id.choices = choice_of_period()
        self.end_time_type.choices = (('period_id', '节数'), ('time', '时间点'))

    def validate_end_date(self, field):
        if self.end_date.data < datetime.datetime.now().date():
            raise ValidationError('结束日期必须大于等于今天')

    def validate_end_period_id(self, field):
        if self.end_time_type.data == 'period_id':
            p = Period.query.filter_by(id=self.end_period_id.data).first()
            if not p:
                raise ValidationError('结束节数不是有效的节数')
            if p.end_time < datetime.datetime.now().time():
                raise ValidationError('结束节数结束时间必须大于当前时间')

    def validate_end_time(self, field):
        if self.end_time_type.data == 'time':
            if not self.end_time.data or not self.end_time.data.time():
                raise ValidationError('结束时间不能为空')
            if self.end_date.data == datetime.datetime.now().date():
                if self.end_time.data.time() <= datetime.datetime.now().time():
                    raise ValidationError('结束时间必须大于当前时间')