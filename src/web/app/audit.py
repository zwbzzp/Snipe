# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# comment
#
# 7/14/16 bitson : Init

import time
import logging
import datetime
import math
from intervaltree import IntervalTree

from .models import Lesson, Desktop, Course, DesktopType
from .license.utils import LicenseUtils
from phoenix.cloud import compute

LOG = logging.getLogger(__name__)


# cache of flavors
def refresh_flavors_cache():
    flavors = compute.list_flavors()
    global flavors_cache
    flavors_cache = {}
    for flavor in flavors:
        flavors_cache[flavor.id] = flavor


def get_flavor(flavor_ref):
    global flavors_cache
    return flavors_cache.get(flavor_ref, None)


class ResourceAuditor(object):

    __auditorname__ = None

    start_datetime = 0
    end_datetime = 0

    def __init__(self):
        self.license = LicenseUtils()
        self.license_info = self.license.get_license_info()

    def audit_now(self, increment):
        """
        audit current used resource
        :param increment:
        :return:
        """
        resource_now = 0
        up_status = ['ACTIVE']
        desktops = self.get_desktops(up_status)
        for desktop in desktops:
            desktop_resource = self.get_desktop_resource(desktop)
            resource_now += desktop_resource

        check_resource = resource_now + increment
        difference = self.check_resource_max(check_resource)
        if difference >= 0:
            LOG.info('audit now pass for auditor %s, difference %s' % (self.__auditorname__, difference))
        else:
            LOG.info('audit now fail for auditor %s, difference %s' % (self.__auditorname__, difference))

        return difference

    def audit_schedule(self, increment, start_datetime, end_datetime, exclude_lesson_id=None):
        """
        audit schedule resource
        :param increment:
        :param start_datetime:
        :param end_datetime:
        :return:
        """
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime

        start = time.clock()
        scheduled_resource = self.get_all_scheduled_resource(exclude_lesson_id)
        end = time.clock()
        LOG.info('calculate scheduled resource use %s' % (end-start))
        LOG.info('audit %s course resource equal to %s s' % (self.__auditorname__, scheduled_resource))

        start = time.clock()
        static_resource = self.get_all_static_resource()
        end = time.clock()
        LOG.info('calculate static resource use %s' % (end-start))
        LOG.info('audit %s other resource equal to %s s' % (self.__auditorname__,  static_resource))

        check_resource = scheduled_resource + static_resource + increment
        LOG.info('audit %s all resource equal to %s' % (self.__auditorname__,  check_resource))

        start = time.clock()
        difference = self.check_resource_max(check_resource)
        end = time.clock()
        LOG.info('check difference use %s s' % (end-start))
        if difference >= 0:
            LOG.info('audit schedule pass for auditor %s, difference %s' % (self.__auditorname__, difference))
        else:
            LOG.info('audit schedule fail for auditor %s, difference %s' % (self.__auditorname__, difference))

        return difference

    def get_all_scheduled_resource(self, exclude_lesson_id):
        """
        calculate the max scheduled resource used between start date time and end date time
        :return: max scheduled resource between the period given
        """
        overlap_course_resource = 0
        tree = IntervalTree()
        sorted_list = []
        start = time.clock()
        lessons = self.get_scheduled_lessons(self.start_datetime, self.end_datetime, exclude_lesson_id)
        end = time.clock()
        LOG.info('step 1 get lessons use %s s' % (end-start))
        start = time.clock()
        for lesson in lessons:
            start_datetime_stamp = datetime.datetime.\
                combine(lesson.start_date, lesson._start_time).timestamp()
            end_datetime_stamp = datetime.datetime.\
                combine(lesson.end_date, lesson._end_time).timestamp()

            # construct interval tree
            upper_stamp = self.start_datetime.timestamp() if start_datetime_stamp < self.start_datetime.timestamp() \
                else start_datetime_stamp
            lower_stamp = self.end_datetime.timestamp() if end_datetime_stamp > self.end_datetime.timestamp() \
                else end_datetime_stamp

            tree[upper_stamp:lower_stamp] = self.get_lesson_resource(lesson)

            # sorted list
            sorted_list.append(upper_stamp)
            sorted_list.append(lower_stamp)
            sorted_list = list(set(sorted_list))
            sorted_list.sort()
        end = time.clock()
        LOG.info('step 2 construct interval tree use %s s' % (end-start))

        start = time.clock()
        # search intervals with the interval tree
        length = len(sorted_list)
        for i in range(length):
            if i < length - 1:
                sorted_tree = sorted(tree[sorted_list[i]:sorted_list[i + 1]])
                tmp_resource = 0
                for n in sorted_tree:
                    tmp_resource += n.data
                overlap_course_resource = \
                    tmp_resource if tmp_resource > overlap_course_resource else overlap_course_resource
        end = time.clock()
        LOG.info('step 3 search tree and get max use %s s' % (end-start))
        return overlap_course_resource

    def get_all_static_resource(self):
        """
        calculate all static resource,
        :return: the static resource used in the given period
        """
        other_resource = 0
        desktops = Desktop.query.filter(Desktop.desktop_type == DesktopType.STATIC).all()
        for desktop in desktops:
            other_resource += self.get_desktop_resource(desktop)
        return other_resource

    def get_lesson_resource(self, lesson):
        """
        get the resource used for the given lesson
        :param lesson:
        :return:
        """
        raise NotImplementedError

    def get_desktop_resource(self, desktop):
        """
        get the resource used for the give desktop
        :param desktop:
        :return:
        """
        raise NotImplementedError

    def check_resource_max(self, check_resource):
        """
        check if the create the 'check resource' will exceed system limitation
        :param check_resource:
        :return: True for passing the check, else False
        """
        raise NotImplementedError

    @staticmethod
    def get_scheduled_lessons(start_datetime, end_datetime, exclude_lesson_id=None):
        query = Lesson.query_lessons(start_datetime, end_datetime, [exclude_lesson_id])
        lessons = query.all()
        return lessons

    @staticmethod
    def get_desktops(status=None):
        if not status:
            desktops = Desktop.query.all()
            return desktops
        else:
            active_desktops = []
            desktops = Desktop.query.all()
            for desktop in desktops:
                try:
                    vm = compute.get_server(desktop.vm_ref)
                    if vm.status in status:
                        active_desktops.append(desktop)
                except:
                    LOG.exception('can not get vm of desktop %s during audit' % desktop.id)
            return active_desktops


##############################
#   types of resource auditor
##############################

class VcpuAuditor(ResourceAuditor):

    __auditorname__ = 'vcpu'

    def get_lesson_resource(self, lesson):
        # flavor = compute.get_flavor(lesson.course.flavor_ref)
        flavor = get_flavor(lesson.course.flavor_ref)
        resource = flavor.vcpus if flavor else 0

        desktop_count = lesson.course.desktops.count()
        count = lesson.course.capacity \
            if lesson.course.capacity >= desktop_count else desktop_count
        course_resource = resource * count
        return course_resource

    def get_desktop_resource(self, desktop):
        try:
            flavor = get_flavor(desktop.flavor_ref)
            desktop_resource = flavor.vcpus if flavor else 0
            return desktop_resource
        except:
            LOG.exception('can not get resource of desktop %s during audit' % desktop.id)
            return 0

    def check_resource_max(self, check_resource):
        resource_max = int(self.license_info[3])
        return resource_max - check_resource

    def __repr__(self):
        return self.__auditorname__


class RamAuditor(ResourceAuditor):

    __auditorname__ = 'ram'

    def get_lesson_resource(self, lesson):
        # flavor = compute.get_flavor(lesson.course.flavor_ref)
        flavor = get_flavor(lesson.course.flavor_ref)
        resource = flavor.ram if flavor else 0

        desktop_count = lesson.course.desktops.count()
        count = lesson.course.capacity \
            if lesson.course.capacity >= desktop_count else desktop_count
        course_resource = resource * count
        return course_resource

    def get_desktop_resource(self, desktop):
        try:
            flavor = get_flavor(desktop.flavor_ref)
            desktop_resource = flavor.ram if flavor else 0
            return desktop_resource
        except:
            LOG.exception('can not get resource of desktop %s during audit' % desktop.id)
            return 0

    def check_resource_max(self, check_resource):
        resource_max = int(self.license_info[4])
        return resource_max - check_resource

    def __repr__(self):
        return self.__auditorname__


class DiskAuditor(ResourceAuditor):

    __auditorname__ = 'disk'

    def get_lesson_resource(self, lesson):
        # flavor = compute.get_flavor(lesson.course.flavor_ref)
        flavor = get_flavor(lesson.course.flavor_ref)
        resource = flavor.disk if flavor else 0

        desktop_count = lesson.course.desktops.count()
        count = lesson.course.capacity \
            if lesson.course.capacity >= desktop_count else desktop_count
        course_resource = resource * count
        return course_resource

    def get_desktop_resource(self, desktop):
        try:
            flavor = get_flavor(desktop.flavor_ref)
            desktop_resource = flavor.disk if flavor else 0
            return desktop_resource
        except:
            LOG.exception('can not get resource of desktop %s during audit' % desktop.id)
            return 0

    def check_resource_max(self, check_resource):
        resource_max = int(self.license_info[5])
        return resource_max - check_resource

    def __repr__(self):
        return self.__auditorname__


class DesktopCountAuditor(ResourceAuditor):

    __auditorname__ = 'desktop_count'

    def get_lesson_resource(self, lesson):
        desktop_count = lesson.course.desktops.count()
        count = lesson.course.capacity \
            if lesson.course.capacity >= desktop_count else desktop_count
        return count

    def get_desktop_resource(self, desktop):
        return 1

    def check_resource_max(self, check_resource):
        resource_max = int(self.license_info[0])
        return resource_max - check_resource

    def __repr__(self):
        return self.__auditorname__

##############################
#   resource controller
##############################


class ResourceController(object):

    def __init__(self):

        refresh_flavors_cache()

        # init auditors
        self.auditors = {
            'vcpu': VcpuAuditor(),
            'ram': RamAuditor(),
            'disk': DiskAuditor(),
            'desktop_count': DesktopCountAuditor()
        }

    def audit_schedule_lesson(self, lesson):
        start_datetime = datetime.datetime.combine(lesson.start_date, lesson._start_time)
        end_datetime = datetime.datetime.combine(lesson.end_date, lesson._end_time)
        course = lesson.course if lesson.course else \
            Course.query.filter(Course.id == lesson.course_id).first()
        start1 = time.clock()
        flavor = get_flavor(course.flavor_ref)
        end1 = time.clock()
        LOG.info('get flavor %s s' % (end1-start1))
        if flavor:
            vcpus = flavor.vcpus
            ram = flavor.ram
            disk = flavor.disk
        else:
            vcpus = 0
            ram = 0
            disk = 0
        desktop_count = course.capacity

        resources_increment = {'vcpu': vcpus * desktop_count,
                               'ram': ram * desktop_count,
                               'disk': disk * desktop_count,
                               'desktop_count': desktop_count}

        exclude_lesson_id = lesson.id if lesson.id else None

        return self.audit_schedule(resources_increment, start_datetime, end_datetime, exclude_lesson_id)

    def audit_schedule(self, resources_increment, start_datetime, end_datetime, exclude_lesson_id=None, type='all'):
        """
        :param resources_increment:
        :param start_datetime:
        :param end_datetime:
        :param type:
        :return: True if pass audit, else False
        """
        audit_detail = self.audit_schedule_with_detail(resources_increment, start_datetime, end_datetime,
                                                       exclude_lesson_id, type)
        for name, result in audit_detail.items():
            if result < 0:
                return False
        return True

    def audit_schedule_with_detail(self, resources_increment, start_datetime, end_datetime,
                                   exclude_lesson_id=None, type='all'):
        """
        :param resources_increment:
            a dict of resource name and its incremental to be audited.
                e.p:
                {
                    'vcpu': 50,
                    'ram': 200,
                    'disk': 500
                    'desktop_count': 10
                 }
        :param type:
            'all': audit by all auditors and return all audit result

            'any': audit by auditors one by one. stop and return result once not pass by any auditor

        :return:
            a dict describe audit results
                e.p:
                {
                    'vcpu': True,
                    'ram': True,
                    'disk': True,
                    'desktop_count': False
                }
        """
        detail = {}

        audit_start = time.clock()
        for name, increment in resources_increment.items():
            auditor = self.auditors.get(name, None)
            if auditor:
                start = time.clock()
                detail[name] = auditor.audit_schedule(increment, start_datetime, end_datetime, exclude_lesson_id)
                end = time.clock()
                LOG.info('auditor %s use %s s' % (name, (end-start)))
                LOG.info('auditor %s result %s' % (name, detail[name]))
                if type == 'any' and detail[name] < 0:
                    break
            else:
                raise Exception('auditor not exist')
        audit_end = time.clock()
        LOG.info('audit_schedule_with_detail use %s s' % (audit_end-audit_start))
        return detail

    def lesson_max_desktop_count(self, lesson):
        course = lesson.course if lesson.course else \
            Course.query.filter(Course.id == lesson.course_id).first()
        # flavor = compute.get_flavor(course.flavor_ref)
        flavor = get_flavor(course.flavor_ref)
        if flavor:
            _vcpu = int(flavor.vcpus)
            _ram = int(flavor.ram)
            _disk = int(flavor.disk)
        else:
            _vcpu = 0
            _ram = 0
            _disk = 0
        _desktop_count = course.capacity

        deduct = 0
        differences = self.audit_current_lesson(lesson)
        for name, difference in differences.items():
            if difference < 0:
                if name == 'vcpu':
                    count = abs(math.ceil(difference / _vcpu))
                elif name == 'ram':
                    count = abs(math.ceil(difference / _ram))
                elif name == 'disk':
                    count = abs(math.ceil(difference / _disk))
                elif name == 'desktop_count':
                    count = abs(difference)

                deduct = count if count > deduct else deduct

        return course.capacity - deduct

    def audit_current_with_detail(self, resources_increment, type='all'):
        detail = {}
        for name, increment in resources_increment.items():
            auditor = self.auditors.get(name, None)
            if auditor:
                detail[name] = auditor.audit_now(increment)
                LOG.info('auditor now %s result %s' % (name, detail[name]))
                if type == 'any':
                    break
            else:
                raise Exception('auditor not exist')
        return detail

    def audit_current_lesson(self, lesson):
        course = lesson.course if lesson.course else \
            Course.query.filter(Course.id == lesson.course_id).first()
        # flavor = compute.get_flavor(course.flavor_ref)
        flavor = get_flavor(course.flavor_ref)
        if flavor:
            vcpus = flavor.vcpus
            ram = flavor.ram
            disk = flavor.disk
        else:
            vcpus = 0
            ram = 0
            disk = 0
        desktop_count = course.capacity

        resources_increment = {'vcpu': vcpus * desktop_count,
                               'ram': ram * desktop_count,
                               'disk': disk * desktop_count,
                               'desktop_count': desktop_count}

        return self.audit_current_with_detail(resources_increment)

    def audit_static_desktop(self, flavor_ref):
        # flavor = compute.get_flavor(flavor_ref)
        flavor = get_flavor(flavor_ref)
        if flavor:
            vcpus = flavor.vcpus
            ram = flavor.ram
            disk = flavor.disk
        else:
            vcpus = 0
            ram = 0
            disk = 0
        desktop_count = 1

        resources_increment = {'vcpu': vcpus,
                               'ram': ram,
                               'disk': disk,
                               'desktop_count': desktop_count}
        start_datetime = datetime.datetime.now()
        end_datetime = datetime.datetime(9999, 12, 31)

        return self.audit_schedule(resources_increment, start_datetime, end_datetime)

    def supply_max_desktop_count(self, course, except_count):
        lesson = course.find_current_lesson()
        # flavor = compute.get_flavor(course.flavor_ref)
        flavor = get_flavor(course.flavor_ref)
        if flavor:
            _vcpu = int(flavor.vcpus)
            _ram = int(flavor.ram)
            _disk = int(flavor.disk)
        else:
            _vcpu = 0
            _ram = 0
            _disk = 0
        _desktop_count = course.capacity

        deduct = 0
        differences = self.audit_supply_course_desktop(course, except_count)
        for name, difference in differences.items():
            if difference < 0:
                if name == 'vcpu':
                    count = abs(math.ceil(difference / _vcpu))
                elif name == 'ram':
                    count = abs(math.ceil(difference / _ram))
                elif name == 'disk':
                    count = abs(math.ceil(difference / _disk))
                elif name == 'desktop_count':
                    count = abs(difference)

                deduct = count if count > deduct else deduct

        return except_count - deduct

    def audit_supply_course_desktop(self, course, count):
        lesson = course.find_current_lesson()

        start_datetime = datetime.datetime.combine(lesson.start_date, lesson._start_time)
        end_datetime = datetime.datetime.combine(lesson.end_date, lesson._end_time)
        course = lesson.course
        # flavor = compute.get_flavor(course.flavor_ref)
        flavor = get_flavor(course.flavor_ref)
        if flavor:
            vcpus = flavor.vcpus
            ram = flavor.ram
            disk = flavor.disk
        else:
            vcpus = 0
            ram = 0
            disk = 0

        resources_increment = {'vcpu': vcpus * count,
                               'ram': ram * count,
                               'disk': disk * count,
                               'desktop_count': count}

        return self.audit_schedule_with_detail(resources_increment, start_datetime, end_datetime)
