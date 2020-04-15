import base64
import datetime
import time

import requests
from flask.json import jsonify
from sqlalchemy import or_, and_

from . import service_counter_blu
from ... import redis_store, db
from flask import request, g
from ...model.model import MDAttachment, MdService_Cluster, MDService, MDService_Type, MDService_Item, MDGoods, \
    MDService_list, MDGoods, MDService_list_goods, MDService_list_contact, MDUSA_service_item, MDService_Item_agent, \
    MDContacts, MDService_list_taskList, MDuser, MDService_Item_solution
from ...utils.logger_factory import logger
from ...config.config import Config
from ...utils.common import user_login_data
from ...config.constants import PER_PAGE, SERVICE_STATUS, TASK_STATUS, SERVICE_STATUS_LIST
import traceback

from ...utils.state_transition import urgency_transition, scope_transition, service_list_status_transition, \
    service_list_task_status_transition
from ...utils.request_utils import WorkFlowAPiRequest
from ...config.urls import TICKET_STEPS


@service_counter_blu.route("/list", methods=["GET"])
@user_login_data
def service_counter_list():
    try:
        user = g.user

        service_item_agent = user.service_item_agent.filter(MDService_Item_agent.status == 1).all()
        if not service_item_agent:
            return jsonify({"status": 2, "msg": "您没有分配权限，请联系系统管理员"})
        service_item_id_list = []
        for each in service_item_agent:
            service_item_id_list.append(each.service_item.id)

        # 获取参数
        status = request.args.get("status", None)
        scope = request.args.get("scope", None)
        urgency = request.args.get("urgency", None)
        page = request.args.get("page", "1")
        per_page = request.args.get("per_page", PER_PAGE)

        # 2 校验
        try:
            page = int(page)
            per_page = int(per_page)
        except Exception as e:
            logger.error(e)
            raise Exception("参数错误")

        if not all([status, scope, urgency]):
            raise Exception("参数缺失")
        # 3 查询数据
        filters = [MDService_list.service_item_id.in_(service_item_id_list)]
        if status != "all":
            status = int(status)
            if status == 1:
                filters.append(MDService_list.service_status == SERVICE_STATUS["allot"])
            elif status == 2:
                filters.append(and_(MDService_list.agent_id == user.id,
                                    MDService_list.service_status.in_(SERVICE_STATUS_LIST[2:6])))
            elif status == 3:
                filters.append(and_(MDService_list.agent_id == user.id,
                                    MDService_list.service_status == SERVICE_STATUS["closeing"]))
            else:
                filters.append(and_(MDService_list.agent_id == user.id,
                                    MDService_list.service_status.in_(SERVICE_STATUS_LIST[6:])))
        else:

            filters.append(or_((MDService_list.service_status == SERVICE_STATUS["allot"]),
                               (and_(MDService_list.service_status.in_(SERVICE_STATUS_LIST[2:]),
                                     MDService_list.agent_id == user.id))))

        if scope != "all":
            scope = int(scope)
            filters.append(MDService_list.scope == scope)
        if urgency != "all":
            urgency = int(urgency)
            filters.append(MDService_list.urgency == urgency)

        try:
            paginate = MDService_list.query.filter(*filters).order_by(MDService_list.create_date.desc()).paginate(page,
                                                                                                                  per_page,
                                                                                                                  False)
        except Exception as e:
            logger.error(e)
            raise Exception("数据查询失败")
        service_list_model_list = paginate.items
        total_page = paginate.pages
        current_page = paginate.page

        service_list_dict_li = []
        for service_list in service_list_model_list:
            service_list_dict = service_list.to_basic_dict()
            service_list_dict["goods_list"] = ""
            goods_obj_list = service_list.goods.all()

            if goods_obj_list:
                goods_name_list = []
                for goods in goods_obj_list[:3]:
                    goods_name_list.append(goods.goods.name)
                service_list_dict["goods_list"] = "; ".join(goods_name_list)
            service_list_dict_li.append(service_list_dict)

        data = {
            "total_page": total_page,
            "current_page": current_page,
            "service_list_dict_li": service_list_dict_li
        }
        return jsonify({"status": 1, "data": data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@service_counter_blu.route("/info", methods=["GET"])
@user_login_data
def service_counter_info():
    try:
        user = g.user
        # 获取参数
        service_list_id = request.args.get("service_list_id", None)
        # 2 校验
        if service_list_id is None:
            raise Exception("service_list_id缺失")
        # 3 查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")

        resp_data = {}
        # TODO 父工单留待日后
        # resp_data["name"] = user.name
        # resp_data["org"] = user.contacts.organization.name

        resp_data["name"] = service_list.user.name
        if service_list.user.contacts:
            resp_data["org"] = service_list.user.contacts.organization.name
        else:
            resp_data["org"] = "无"
        resp_data["title"] = service_list.title
        resp_data["service_item"] = service_list.service_item.name
        resp_data["price"] = round(float(service_list.price), 2) if service_list.price else 0
        resp_data["scope"] = scope_transition(service_list.scope)
        resp_data["urgency"] = urgency_transition(service_list.urgency)
        resp_data["descript"] = service_list.descript

        goods_list = []
        goods_obj_list = service_list.goods.all()
        for each_goods in goods_obj_list:
            each_goods_dict = {}
            each_goods_dict["name"] = each_goods.goods.name
            each_goods_dict["qty"] = each_goods.qty
            goods_list.append(each_goods_dict)

        resp_data["goods_list"] = goods_list

        mandator_list = []
        mandator_obj_list = service_list.contact.all()
        for each_mandator in mandator_obj_list:
            each_mandator_dict = {}
            each_mandator_dict["id"] = each_mandator.id
            each_mandator_dict["name"] = each_mandator.name
            each_mandator_dict["phone"] = each_mandator.phone
            each_mandator_dict["memo"] = each_mandator.memo
            mandator_list.append(each_mandator_dict)

        resp_data["mandator_list"] = mandator_list

        closeing_flag = True
        worker_list = []
        worker_obj_list = service_list.task_list.all()
        for each_worker in worker_obj_list:
            each_worker_dict = {}
            each_worker_dict["task_id"] = each_worker.id
            each_worker_dict["id"] = each_worker.worker.id
            each_worker_dict["title"] = each_worker.name
            each_worker_dict["name"] = each_worker.worker.name
            each_worker_dict["phone"] = each_worker.worker.contacts.phone
            each_worker_dict["org"] = each_worker.worker.contacts.organization.name
            each_worker_dict["status"] = service_list_task_status_transition(each_worker.status)
            each_worker_dict["status_id"] = each_worker.status
            if each_worker.status == TASK_STATUS["end"]:
                each_worker_dict["closeing_statment"] = each_worker.closeing_statment
            worker_list.append(each_worker_dict)
            if each_worker.status != TASK_STATUS["end"]:
                closeing_flag = False

        resp_data["worker_list"] = worker_list
        resp_data["closeing_flag"] = 0
        if len(worker_list) > 0 and closeing_flag and service_list.service_status == SERVICE_STATUS["closeing"]:
            resp_data["closeing_flag"] = 1
        resp_data["service_status"] = service_list.service_status
        resp_data["status"] = service_list_status_transition(service_list.service_status)

        resp_data["closeing_solution"] = ""
        resp_data["closeing_statment"] = ""
        if service_list.service_status in [SERVICE_STATUS["grade"], SERVICE_STATUS["end"]]:
            resp_data["closeing_solution"] = service_list.service_item_solution.name
            resp_data["closeing_statment"] = service_list.closeing_statment

        return jsonify({"status": 1, "data": resp_data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@service_counter_blu.route("/get_worker", methods=["GET"])
@user_login_data
def get_worker():
    try:
        user = g.user
        # 获取参数
        service_list_id = request.args.get("service_list_id", None)
        # 2 校验
        if service_list_id is None:
            raise Exception("service_list_id缺失")
        # 3 查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")
        try:
            worker_obj_list = service_list.service_item.service_contract.service_vendor.organization.contacts.filter(
                MDContacts.bind_status == 1).all()
        except:
            raise Exception("获取服务人员信息失败")

        task_list = service_list.task_list.filter(
            MDService_list_taskList.status.notin_([TASK_STATUS["cancel"], TASK_STATUS["reject"]])).all()

        exist_worker_id = [each.worker_id for each in task_list]

        worker_info_list = []
        for each_worker in worker_obj_list:
            worker_id = each_worker.user.first().id
            if worker_id in exist_worker_id:
                continue
            worker_dict = {}
            worker_dict["title"] = each_worker.name
            worker_dict["label"] = each_worker.organization.name
            worker_dict["value"] = str(worker_id)
            worker_info_list.append(worker_dict)

        return jsonify({"status": 1, "worker_list": worker_info_list})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@service_counter_blu.route("/allot_worker", methods=["POST"])
@user_login_data
def allot_worker():
    try:
        user = g.user
        # 获取参数
        data = request.json
        service_list_id = data.get("service_list_id", None)
        worker_id = data.get("worker_id", None)
        remark_value = data.get("remark_value", None)
        task_name = data.get("task_name", None)
        # 2 校验
        if not all([service_list_id, worker_id, remark_value, task_name]):
            raise Exception("参数缺失")
        worker_id = int(worker_id)
        # 3 查询数据

        worker = MDuser.query.filter(MDuser.id == worker_id).first()
        if not worker:
            raise Exception("该服务人员不存在")

        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")

        if service_list.agent is not None and service_list.agent_id != user.id:
            return jsonify({"status": 2, "msg": "该工单已由其他受理人受理"})

        service_list.agent = user
        this_time = time.time()
        service_list_task_list = MDService_list_taskList()
        service_list_task_list.service_list = service_list
        service_list_task_list.name = task_name
        service_list_task_list.descript = remark_value
        service_list_task_list.worker_id = worker_id
        service_list_task_list.create_date = this_time
        service_list_task_list.status = TASK_STATUS["answer"]

        if not service_list.assign_date:
            service_list.assign_date = this_time
        if service_list.service_status == SERVICE_STATUS["allot"]:
            service_list.service_status = SERVICE_STATUS["answer"]
        elif service_list.service_status == SERVICE_STATUS["closeing"]:
            service_list.service_status = SERVICE_STATUS["answer"]

        try:
            db.session.add(service_list_task_list)
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存工作任务表信息失败")

        # data = {
        #     "id": worker.id,
        #     "name": worker.name,
        #     "org": worker.contacts.organization.name,
        #     "phone": worker.contacts.phone
        # }

        return jsonify({"status": 1, "msg": "OK"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "分配失败"})


@service_counter_blu.route("/service_item_solution", methods=["GET"])
@user_login_data
def get_service_item_solution():
    try:
        user = g.user
        # 获取参数
        service_list_id = request.args.get("service_list_id", None)
        # 2 校验
        if service_list_id is None:
            raise Exception("service_list_id缺失")

        # 3 查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")
        try:
            service_item_solution_obj_list = service_list.service_item.service_item_solution.filter(
                MDService_Item_solution.status == 1).all()
        except:
            raise Exception("获取服务项解决方案失败")

        service_item_solution_list = []
        for each in service_item_solution_obj_list:
            each_dict = {}
            each_dict["title"] = each.name
            each_dict["value"] = str(each.id)
            service_item_solution_list.append(each_dict)

        return jsonify({"status": 1, "service_item_solution_list": service_item_solution_list})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@service_counter_blu.route("/closeing", methods=["POST"])
@user_login_data
def closeing():
    try:
        user = g.user
        # 获取参数
        data = request.json
        service_list_id = data.get("service_list_id", None)
        soluation_id = data.get("soluation_id", None)
        remark_value = data.get("remark_value", None)
        # 2 校验
        if service_list_id is None:
            raise Exception("service_list_id缺失")
        if soluation_id is None:
            raise Exception("soluation_id缺失")
        if remark_value is None:
            raise Exception("remark_value缺失")

        soluation_id = int(soluation_id)

        # 3 查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")

        if service_list.service_status != SERVICE_STATUS["closeing"]:
            raise Exception("该工单不可结案")
        this_time = time.time()
        service_list.resolve_date = this_time
        service_list.solution_id = soluation_id
        service_list.closeing_statment = remark_value
        service_list.service_status = SERVICE_STATUS["grade"]

        service_list_goods = service_list.goods.all()
        for each in service_list_goods:
            each.create_date = this_time
        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存结案信息失败")

        return jsonify({"status": 1, "msg": "OK"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "结案失败"})


@service_counter_blu.route("/reject_task", methods=["POST"])
@user_login_data
def reject_task():
    try:
        user = g.user
        # 获取参数
        data = request.json
        service_list_id = data.get("service_list_id", None)
        task_id = data.get("task_id", None)

        # 2 校验
        if not all([service_list_id, task_id]):
            raise Exception("参数缺失")
        # 3 查询数据

        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")

        service_task = MDService_list_taskList.query.filter(MDService_list_taskList.id == task_id).first()
        if not service_task:
            raise Exception("该任务不存在")

        service_list_task_list = service_list.task_list.filter(
            MDService_list_taskList.status.notin_([TASK_STATUS["cancel"], TASK_STATUS["reject"]])).all()
        if len(service_list_task_list) == 1 and service_list_task_list[0] is service_task:
            service_list.service_status = SERVICE_STATUS["allot"]

        service_task.close_date = time.time()
        service_task.status = TASK_STATUS["reject"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存任务信息失败")

        return jsonify({"status": 1, "msg": "OK"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "分配失败"})
