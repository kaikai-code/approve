import base64
import datetime
import time

import requests
from flask.json import jsonify
import json
from . import my_approve_blu
from ... import redis_store, db
from flask import request, g
from ...model.model import MDAttachment, MdService_Cluster, MDService, MDService_Type, MDService_Item, MDGoods, MDService_list, MDGoods, MDService_list_goods, MDService_list_contact, MDUSA_service_item
from ...utils.logger_factory import logger
from ...config.config import Config
from ...utils.common import user_login_data
from ...config.constants import PER_PAGE, SERVICE_LIST_TICK_ID_REDIS_EXPIRES, SERVICE_STATUS
import traceback

from ...utils.state_transition import urgency_transition, scope_transition
from ...utils.request_utils import WorkFlowAPiRequest
from ...config.urls import MY_APPROVE, DISPOSE_TICKET, GET_TICKET_OPERATION, APPROVE_SERVICE_LIST, GET_SERVICE_LIAT_STATUS


@my_approve_blu.route("/list", methods=["GET"])
@user_login_data
def my_approve_list():

    try:
        user = g.user
        # 获取参数
        status = request.args.get("status", None)
        scope = request.args.get("scope", None)
        urgency = request.args.get("urgency", None)
        page = request.args.get("page", "1")
        per_page = request.args.get("per_page", PER_PAGE)

        #2 校验
        try:
            page = int(page)
            per_page = int(per_page)
        except Exception as e:
            logger.error(e)
            raise Exception("参数错误")
        if not all([status, scope, urgency]):
            raise Exception("参数缺失")

        try:
            if status == "1":
                service_list_tick_id_list = redis_store.get("service_list_tick_id_list_duty" + str(user.id))

            elif status == "2":
                service_list_tick_id_list = redis_store.get("service_list_tick_id_list_worked" + str(user.id))
            else:
                service_list_tick_id_list = redis_store.get("service_list_tick_id_list_all" + str(user.id))
        except Exception as e:
            logger.error(e)
            raise Exception("数据查询失败")

        if not service_list_tick_id_list:

            ins = WorkFlowAPiRequest(username=user.nickname)
            param = {
                "per_page": 999999
            }

            if status == "1":
                url = MY_APPROVE.format("duty")
                rstatus, resp = ins.getdata(parameters=param, method='get', url=url)
                print(rstatus)
                print(resp)
                if not rstatus:
                    raise Exception("获取我的审批失败")
                # 我的待审批
                data_list = resp["data"].get("value")
                service_list_tick_id_list = []
                for each in data_list:
                    service_list_tick_id_list.append(each["id"])
                service_list_tick_id_list = list(set(service_list_tick_id_list))
                print(service_list_tick_id_list)
                try:
                    redis_store.set("service_list_tick_id_list_duty" + str(user.id),
                                    json.dumps(service_list_tick_id_list), SERVICE_LIST_TICK_ID_REDIS_EXPIRES)
                except Exception as e:
                    logger.error(e)
                    raise Exception("service_list_tick_id_list保存失败")
            elif status == "2":
                url = MY_APPROVE.format("worked")
                rstatus, resp = ins.getdata(parameters=param, method='get', url=url)
                print(rstatus)
                print(resp)
                if not rstatus:
                    raise Exception("获取我的审批失败")

                # 我的已审批
                data_list = resp["data"].get("value")
                service_list_tick_id_list = []
                for each in data_list:
                    service_list_tick_id_list.append(each["id"])
                service_list_tick_id_list = list(set(service_list_tick_id_list))
                print(service_list_tick_id_list)
                try:
                    redis_store.set("service_list_tick_id_list_worked" + str(user.id),
                                    json.dumps(service_list_tick_id_list), SERVICE_LIST_TICK_ID_REDIS_EXPIRES)
                except Exception as e:
                    logger.error(e)
                    raise Exception("service_list_tick_id_list保存失败")
            else:
                url1 = MY_APPROVE.format("duty")
                rstatus1, resp1 = ins.getdata(parameters=param, method='get', url=url1)
                print(rstatus1)
                print(resp1)
                url2 = MY_APPROVE.format("worked")
                rstatus2, resp2 = ins.getdata(parameters=param, method='get', url=url2)
                print(rstatus2)
                print(resp2)
                if not rstatus1 or not rstatus2:
                    raise Exception("获取我的审批失败")

                # 　全部，已审批和待审批
                data_list1 = resp1["data"].get("value")
                data_list2 = resp2["data"].get("value")
                service_list_tick_id_list = []
                for each in data_list1:
                    service_list_tick_id_list.append(each["id"])
                for each in data_list2:
                    service_list_tick_id_list.append(each["id"])

                service_list_tick_id_list = list(set(service_list_tick_id_list))

                print(service_list_tick_id_list)
                try:
                    redis_store.set("service_list_tick_id_list_all" + str(user.id),
                                    json.dumps(service_list_tick_id_list), SERVICE_LIST_TICK_ID_REDIS_EXPIRES)
                except Exception as e:
                    logger.error(e)
                    raise Exception("service_list_tick_id_list保存失败")

        else:
            print("hehe")
            service_list_tick_id_list = json.loads(service_list_tick_id_list)

        total = len(service_list_tick_id_list)

        if total == 0:
            data = {
                "total_page": 0,
                "current_page": 1,
                "service_list_dict_li": []
            }
            return jsonify({"status": 1, "data": data})
        start = page * per_page - per_page
        end = page * per_page
        paging_service_list_tick_id_list = service_list_tick_id_list[start:end]
        filters = [MDService_list.tick_id.in_(paging_service_list_tick_id_list)]
        if scope != "all":
            scope = int(scope)
            filters.append(MDService_list.scope == scope)
        if urgency != "all":
            urgency = int(urgency)
            filters.append(MDService_list.urgency == urgency)

        service_list_model_list = MDService_list.query.filter(*filters).order_by(MDService_list.create_date.desc()).all()

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
        total_page = total // per_page
        page2 = total % per_page
        if page2 != 0:
            total_page += 1
        data = {
            "total_page" : total_page,
            "current_page" : page,
            "service_list_dict_li" : service_list_dict_li
        }
        return jsonify({"status" : 1, "data": data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@my_approve_blu.route("/info", methods=["GET"])
@user_login_data
def my_approve_info():

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
        resp_data["org"] = service_list.user.contacts.organization.name
        resp_data["title"] = service_list.title
        resp_data["service_item"] = service_list.service_item.name
        resp_data["price"] = round(float(service_list.price), 2) if service_list.price else 0
        resp_data["scope"] = scope_transition(service_list.scope)
        resp_data["urgency"] = urgency_transition(service_list.urgency)
        resp_data["descript"] = service_list.descript
        # resp_data["service_status"] = service_list.service_status

        ins = WorkFlowAPiRequest(username=user.nickname)
        param = {
            "per_page": 999999
        }
        url = MY_APPROVE.format("duty")
        rstatus, resp = ins.getdata(parameters=param, method='get', url=url)
        print(rstatus)
        print(resp)
        if not rstatus:
            raise Exception("获取我的审批失败")

        data_list = resp["data"].get("value")
        service_list_tick_id_list = []
        for each in data_list:
            service_list_tick_id_list.append(each["id"])
        print(service_list_tick_id_list)
        resp_data["service_status"] = 1
        print(service_list.tick_id)
        if service_list.tick_id not in service_list_tick_id_list:
            resp_data["service_status"] = 0




        # resp_data["service_status"] = 0
        # if service_list.service_status == 6:
        #     resp_data["service_status"] = 1

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

        ins = WorkFlowAPiRequest(username=user.nickname)
        url = GET_TICKET_OPERATION.format(service_list.tick_id)

        rstatus, resp = ins.getdata(method='get', url=url)
        print(rstatus)
        print(resp)
        if not rstatus:
            raise Exception("获取处理步骤失败")
        try:
            resp_data["aggre_transition_id"] = resp["data"]["value"][0]["transition_id"]
            resp_data["refuse_transition_id"] = resp["data"]["value"][1]["transition_id"]
        except:
            resp_data["aggre_transition_id"] = None
            resp_data["refuse_transition_id"] = None

        return jsonify({"status" : 1, "data": resp_data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})



@my_approve_blu.route("/refuse", methods=["POST"])
@user_login_data
def refuse():

    try:
        user = g.user
        # 获取参数
        data = request.json
        service_list_id = data.get("service_list_id", None)
        transition_id = data.get("transition_id", None)
        refuse_value = data.get("refuse_value", None)


        # 2 校验
        if not all([service_list_id, transition_id, refuse_value]):
            raise Exception("参数不全")

        # 3 查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")

        ins = WorkFlowAPiRequest(username=user.nickname)
        data = {
            "transition_id": transition_id,  # 流转id
            "suggestion": refuse_value,  # 建议
        }
        url = APPROVE_SERVICE_LIST.format(service_list.tick_id)
        rstatus, resp = ins.getdata(method='patch', url=url, data=data)
        print(rstatus)
        print(resp)
        if not rstatus:
            raise Exception("拒绝失败")

        this_time = time.time()
        if not service_list.accept_date:
            service_list.accept_date = this_time
        service_list.advise = refuse_value
        service_list.service_status = SERVICE_STATUS["end"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存信息失败")

        return jsonify({"status" : 1, "msg": "ok"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "拒绝失败"})


@my_approve_blu.route("/aggre", methods=["POST"])
@user_login_data
def aggre():

    try:
        user = g.user
        # 获取参数
        data = request.json
        service_list_id = data.get("service_list_id", None)
        transition_id = data.get("transition_id", None)
        aggre_value = data.get("refuse_value", "")


        # 2 校验
        if not all([service_list_id, transition_id]):
            raise Exception("参数不全")

        # 3 查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")

        ins = WorkFlowAPiRequest(username=user.nickname)
        data = {
            "transition_id": transition_id,  # 流转id
            "suggestion": aggre_value,  # 建议
        }
        url = APPROVE_SERVICE_LIST.format(service_list.tick_id)
        rstatus, resp = ins.getdata(method='patch', url=url, data=data)
        print(rstatus)
        print(resp)
        if not rstatus:
            raise Exception("审批失败")

        this_time = time.time()
        if not service_list.accept_date:
            service_list.accept_date = this_time
        url = GET_SERVICE_LIAT_STATUS.format(service_list.tick_id)
        rstatus, resp = ins.getdata(method='get', url=url)
        # print("当前参与人为空")
        print(rstatus)
        print(resp)
        if not rstatus:
            raise Exception("查询工单状态失败")

        participant_info_list = resp["data"]["participant_info_list"]
        if len(participant_info_list) == 0:
            service_list.service_status = SERVICE_STATUS["allot"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存信息失败")

        return jsonify({"status" : 1, "msg": "ok"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "审批失败"})