# -*- encoding: utf-8 -*-
# Copyright 2016 Vinzor Co.,Ltd.
#
# Schedule view
#
# 2016/3/1 fengyc : Init

import json
from flask import render_template, abort, request, jsonify
from flask.ext.login import login_required, current_user

from ..auth.principal import admin_permission
from . import schedule
from ..celery_sqlalchmey_scheduler_models import DatabaseSchedulerEntry, CrontabSchedule, IntervalSchedule
from ..models import DesktopTask, DesktopType, DesktopState, TaskState, StageResult, Course
from sqlalchemy import or_
from .. import db
from sqlalchemy import asc
from ..jinja_filters import datetime_format
from ..log.utils import UserActionLogger

ua_logger = UserActionLogger()


@schedule.route('/tasks', methods=['GET'])
@login_required
def tasks():
    # 权限检查
    if not admin_permission.can():
        abort(403)

    """ Show all running task
    """
    return render_template('schedule/tasks.html')


@schedule.route('/task_table', methods=['GET'])
@login_required
def task_table():
    # 权限检查
    if not admin_permission.can():
        abort(403)

    """获取task_table指定页所需的task列表
    """
    # 列号对应的排序属性
    col_map = {"0": "id",
               "1": "updated_at",
               "2": "action",
               "3": "state",
               "4": "stage",
               "5": "retries",
               "6": "enabled",
               "7": "result",
               "8": "id",
               "9": "id"}

    sEcho = request.args.get('sEcho')
    iDisplayStart = request.args.get("iDisplayStart")
    iDisplayLength = request.args.get("iDisplayLength")
    sSearch = request.args.get("sSearch")
    iSortCol = request.args.get("iSortCol_0")
    sSortDir = request.args.get("sSortDir_0")
    if iSortCol is None:
        iSortCol = '1'
    if sSortDir is None:
        sSortDir = "desc"
    sort_col = col_map[iSortCol]

    if sSearch == '' or sSearch is None:
        query = DesktopTask.query
        # query = DesktopTask.query.order_by(DesktopTask.result_order, sort_col)    // 结果为ERROR的任务置顶
    else:
        query = DesktopTask.query.filter(or_(
            # DesktopTask.id.like("%"+sSearch+"%"),
            DesktopTask.action.like("%"+sSearch+"%"),
            DesktopTask.state.like("%"+sSearch+"%"),
            DesktopTask.stage.like("%"+sSearch+"%"),
            DesktopTask.retries.like("%"+sSearch+"%"),
            # DesktopTask.enabled.like("%"+sSearch+"%"),
            DesktopTask.result.like("%"+sSearch+"%")))
            # Course.query.filter_by(id=json.loads(DesktopTask.context).course_id).first().name.like("%"+sSearch+"%")))
        # query.order_by(DesktopTask.result_order, sort_col)    // 结果为ERROR的任务置顶

        courses = Course.query.filter(Course.name.like("%"+sSearch+"%")).all()
        for course in courses:
            query_task_for_course = DesktopTask.query.filter(or_(
                DesktopTask.context.like('%"course": '+str(course.id)+',%'),
                DesktopTask.context.like('%"course": '+str(course.id)+'}%')))
            query = query.union(query_task_for_course)

    sort_col = getattr(DesktopTask, sort_col)
    if sSortDir == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    page = int(iDisplayStart) // int(iDisplayLength)
    pagination = query.paginate(page+1, int(iDisplayLength), False)
    task_list = pagination.items
    task_json_list = []
    for item in task_list:
        task_json_list.append(
            {
                'id': item.id,
                'updated_at': datetime_format(item.updated_at),
                'idAndAction': {
                    'id':item.id,
                    'action':item.action
                },
                'state': TaskState.get_state_chs(item.state),
                'stage': item.stage,
                'retries':item.retries,
                'enabled':item.enabled,
                'result':item.result,
                'context':item.context,
                'id_enabled_result':{
                    'id':item.id,
                    'enabled':item.enabled,
                    'result':item.result
                }
            }
        )
    len(task_json_list)
    data = {"sEcho": sEcho,
            "iTotalRecords": str(pagination.total),
            "iTotalDisplayRecords": str(pagination.total),
            "aaData": task_json_list
            }
    db.session.remove()
    return jsonify(data)


@schedule.route('/tasks/<int:id>', methods=['GET'])
@login_required
def task_detail(id):
    # 权限检查
    if not admin_permission.can():
        abort(403)

    """ Show task detail
    """
    task = DesktopTask.query.filter_by(id=id).first()
    if task is None:
        abort(404)
    stage_results = task.stage_results
    task_context_json = json.loads(task.context)
    return render_template('schedule/task_detail.html', stage_results=stage_results, task_context_json=task_context_json)


@schedule.route('/tasks/', methods=['DELETE'])
@login_required
def delete_task():
    # 权限检查
    if not admin_permission.can():
        abort(403)

    result_json = {
        "status": "success",
        "data": {
            "success_list": [],
            "fail_list": []
        }
    }
    # 请求中包含所要删除的task_id列表
    tasks = request.json
    for id in tasks:
        task = DesktopTask.query.filter_by(id=int(id)).first()
        if task:
            stage_results = StageResult.query.filter_by(task_id = task.id).all()
            for stage_result in stage_results:
                db.session.delete(stage_result)
            db.session.delete(task)
            db.session.commit()
            ua_logger.info(current_user, "删除任务: %s" % task.id)
            result_json["data"]["success_list"].append(id)
        else:
            result_json["data"]["fail_list"].append(id)
    return jsonify(result_json)


@schedule.route('/tasks/<string:action>', methods=['PUT'])
@login_required
def tasks_action(action):
    # 权限检查
    if not admin_permission.can():
        abort(403)

    result_json = {
        "status": "success",
        "data": {
            "success_list": [],
            "fail_list": []
        }
    }
    tasks = request.json
    for id in tasks:
        task = DesktopTask.query.filter_by(id=int(id)).first()
        if task:
            if action == "resume":
                # Continue the task from the fail stage
                task.resume()
                ua_logger.info(current_user, "重做任务: %s" % task.id)
            elif action == "reset":
                # Reset the task to the initial state
                task.reset()
                ua_logger.info(current_user, "重置任务: %s" % task.id)
            elif action == "disable":
                # Disable the task
                ua_logger.info(current_user, "禁用任务: %s" % task.id)
                task.disable()
            elif action == "enable":
                # Enable the task
                ua_logger.info(current_user, "启用任务: %s" % task.id)
                task.enable()
            result_json["data"]["success_list"].append(id)
        else:
            result_json["data"]["fail_list"].append(id)
    return jsonify(result_json)






