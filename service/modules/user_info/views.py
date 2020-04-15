import base64
import datetime
import time

import requests
from flask.json import jsonify

from . import user_info_blu
from ... import redis_store, db
from flask import request, g
from ...model.model import MDAttachment, MdService_Cluster, MDService, MDService_Type, MDService_Item, MDGoods, MDService_list, MDGoods, MDService_list_goods, MDService_list_contact, MDUSA_service_item, MDService_Item_evaluate, MDService_list_evaluate, MDService_list_taskList
from ...utils.logger_factory import logger
from ...config.config import Config
from ...utils.common import user_login_data
from ...config.constants import PER_PAGE, SERVICE_STATUS, SERVICE_STATUS_LIST, TASK_STATUS
import traceback

from ...utils.state_transition import urgency_transition, scope_transition, service_list_status_title_transition, service_list_status_transition
from ...utils.request_utils import WorkFlowAPiRequest
from ...config.urls import TICKET_STEPS, MY_APPROVE


@user_info_blu.route("/info", methods=["GET"])
@user_login_data
def user_info():

    try:
        user = g.user
        # 获取参数

        resp_data = {}
        resp_data["name"] = user.name
        resp_data["org"] = user.contacts.organization.name
        resp_data["phone"] = user.contacts.phone

        resp_data["task_count"] = MDService_list_taskList.query.filter(
            MDService_list_taskList.worker_id == user.id,
            MDService_list_taskList.status.in_([TASK_STATUS["answer"], TASK_STATUS["run"],
                                                TASK_STATUS["pause"]])
        ).count()

        resp_data["submit_count"] = MDService_list.query.filter(
            MDService_list.user_id == user.id,
            MDService_list.service_status != SERVICE_STATUS["end"]
        ).count()

        allot_count1 = MDService_list.query.filter(MDService_list.agent_id == user.id,
                                                   MDService_list.service_status.notin_([SERVICE_STATUS["end"],
                                                                                        SERVICE_STATUS["grade"]])).count()
        print("allot_count1", allot_count1)
        agent_service_item_obj_list = user.service_item_agent.all()
        agent_service_item_id_list = [i.service_Item_id for i in agent_service_item_obj_list]
        allot_count2 = MDService_list.query.filter(MDService_list.agent_id.is_(None),
                                                   MDService_list.service_status == SERVICE_STATUS["allot"],
                                                   MDService_list.service_item_id.in_(
                                                         agent_service_item_id_list)).count()
        print("allot_count2", allot_count2)
        resp_data["allot_count"] = allot_count1 + allot_count2

        ins = WorkFlowAPiRequest(username=user.nickname)
        param = {
            "per_page": 999999
        }
        url = MY_APPROVE.format("duty")
        rstatus, resp = ins.getdata(parameters=param, method='get', url=url)
        print(rstatus)
        print(resp)
        if not rstatus:
            raise Exception("获取我的审批信息失败")

        data_list = resp["data"].get("value")
        service_list_tick_id_list = []
        for each in data_list:
            service_list_tick_id_list.append(each["id"])
        print(service_list_tick_id_list)

        resp_data["approve_count"] = MDService_list.query.filter(MDService_list.service_status == SERVICE_STATUS["approve"],
                                                                 MDService_list.tick_id.in_(service_list_tick_id_list)).count()


        user_task_list = user.task_list
        all_user_task_list = user_task_list.all()
        total_user_task_list_count = user_task_list.count()
        total_resp_time = 0
        total_run_time = 0
        total_evaluate_count = 0
        total_score = 0
        for each in all_user_task_list:
            if each.response_date:
                resp_time = (each.response_date - each.create_date) / 60
                total_resp_time += resp_time
            if each.close_date and each.response_date:
                run_time = (each.close_date - each.response_date) / 60
                total_run_time += run_time
            this_evaluate = each.service_list.evaluate.all()
            for i in this_evaluate:
                total_score += i.score
                total_evaluate_count += 1
        if total_user_task_list_count == 0:
            resp_data["all_avg_resp_time"] = 0
            resp_data["all_avg_run_time"] = 0
        else:
            resp_data["all_avg_resp_time"] = round(total_resp_time / total_user_task_list_count, 2)
            resp_data["all_avg_run_time"] = round(total_run_time / total_user_task_list_count, 2)
        if total_evaluate_count == 0:
            resp_data["all_avg_score"] = 0.1
        else:
            resp_data["all_avg_score"] = round(total_score / total_evaluate_count, 1)
        resp_data["total_count"] = total_user_task_list_count

        current_month = datetime.datetime.now().date().replace(day=1)
        print(current_month)
        current_month_timestamp = int(time.mktime(current_month.timetuple()))
        filter_user_task_list = user_task_list.filter(MDService_list_taskList.create_date > current_month_timestamp)
        current_month_user_task_list = filter_user_task_list.all()
        current_month_user_task_list_count = filter_user_task_list.count()
        print("current_month_user_task_list_count", current_month_user_task_list_count)
        current_month_resp_time = 0
        current_month_run_time = 0
        current_month_evaluate_count = 0
        current_month_score = 0
        for each in current_month_user_task_list:
            if each.response_date:
                resp_time = (each.response_date - each.create_date) / 60
                current_month_resp_time += resp_time
            if each.close_date and each.response_date:
                run_time = (each.close_date - each.response_date) / 60
                current_month_run_time += run_time
            this_evaluate = each.service_list.evaluate.all()
            for i in this_evaluate:
                current_month_score += i.score
                current_month_evaluate_count += 1
        if current_month_user_task_list_count == 0:
            resp_data["current_month_avg_resp_time"] = 0
            resp_data["current_month_avg_run_time"] = 0
        else:
            resp_data["current_month_avg_resp_time"] = round(current_month_resp_time / current_month_user_task_list_count, 2)
            resp_data["current_month_avg_run_time"] = round(current_month_run_time / current_month_user_task_list_count, 2)
        if current_month_evaluate_count == 0:
            resp_data["current_month_avg_score"] = 0.1
        else:
            resp_data["current_month_avg_score"] = round(current_month_score / current_month_evaluate_count, 1)
        resp_data["current_month_count"] = current_month_user_task_list_count


        print(resp_data)

        return jsonify({"status" : 1, "data": resp_data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@user_info_blu.route("/get_count", methods=["GET"])
@user_login_data
def get_count():

    try:
        user = g.user
        # 获取参数

        resp_data = {}

        resp_data["task_count"] = MDService_list_taskList.query.filter(
            MDService_list_taskList.worker_id == user.id,
            MDService_list_taskList.status.in_([TASK_STATUS["answer"], TASK_STATUS["run"],
                                                TASK_STATUS["pause"]])
        ).count()

        resp_data["submit_count"] = MDService_list.query.filter(
            MDService_list.user_id == user.id,
            MDService_list.service_status != SERVICE_STATUS["end"]
        ).count()

        allot_count1 = MDService_list.query.filter(MDService_list.agent_id == user.id,
                                                   MDService_list.service_status.in_(
                                                       [SERVICE_STATUS["allot"],
                                                        SERVICE_STATUS["answer"],
                                                        SERVICE_STATUS["run"],
                                                        SERVICE_STATUS["pause"],
                                                        SERVICE_STATUS["closeing"]])).count()

        agent_service_item_obj_list = user.service_item_agent.all()
        agent_service_item_id_list = [i.service_Item_id for i in agent_service_item_obj_list]
        allot_count2 = MDService_list.query.filter(MDService_list.agent_id.is_(None),
                                                   MDService_list.service_status == SERVICE_STATUS["allot"],
                                                   MDService_list.service_item_id.in_(
                                                       agent_service_item_id_list)).count()



        resp_data["allot_count"] = allot_count1 + allot_count2

        ins = WorkFlowAPiRequest(username=user.nickname)
        param = {
            "per_page": 999999
        }
        url = MY_APPROVE.format("duty")
        rstatus, resp = ins.getdata(parameters=param, method='get', url=url)
        print(rstatus)
        print(resp)
        if not rstatus:
            raise Exception("获取我的审批信息失败")

        data_list = resp["data"].get("value")
        service_list_tick_id_list = []
        for each in data_list:
            service_list_tick_id_list.append(each["id"])
        print(service_list_tick_id_list)

        resp_data["approve_count"] = MDService_list.query.filter(MDService_list.service_status == SERVICE_STATUS["approve"],
                                                                 MDService_list.tick_id.in_(service_list_tick_id_list)).count()

        return jsonify({"status" : 1, "data": resp_data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})