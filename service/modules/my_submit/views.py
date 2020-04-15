import base64
import datetime
import time

import requests
from flask.json import jsonify

from . import my_submit_blu
from ... import redis_store, db
from flask import request, g
from ...model.model import MDAttachment, MdService_Cluster, MDService, MDService_Type, MDService_Item, MDGoods, MDService_list, MDGoods, MDService_list_goods, MDService_list_contact, MDUSA_service_item, MDService_Item_evaluate, MDService_list_evaluate
from ...utils.logger_factory import logger
from ...config.config import Config
from ...utils.common import user_login_data
from ...config.constants import PER_PAGE, SERVICE_STATUS, SERVICE_STATUS_LIST, TASK_STATUS
import traceback

from ...utils.state_transition import urgency_transition, scope_transition, service_list_status_title_transition, service_list_status_transition, service_list_task_status_transition
from ...utils.request_utils import WorkFlowAPiRequest
from ...config.urls import TICKET_STEPS, GET_SERVICE_LIAT_STATUS


@my_submit_blu.route("/list", methods=["GET"])
@user_login_data
def my_submit_list():

    try:
        # 获取用户对象
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

        #3 查询数据
        filters = [MDService_list.user_id == user.id]
        if status != "all":
            status = int(status)
            if status == 2:
                # 已完成
                filters.append(MDService_list.service_status == SERVICE_STATUS["end"])
            else:
                # 未完成
                filters.append(MDService_list.service_status != SERVICE_STATUS["end"])
        if scope != "all":
            # 按范围筛选
            scope = int(scope)
            filters.append(MDService_list.scope == scope)
        if urgency != "all":
            # 按紧急度筛选
            urgency = int(urgency)
            filters.append(MDService_list.urgency == urgency)

        try:
            # 分页读取工单信息
            paginate = MDService_list.query.filter(*filters).order_by(MDService_list.create_date.desc()).paginate(page,per_page,False)
        except Exception as e:
            logger.error(e)
            raise Exception("数据查询失败")
        # 工单对象列表
        service_list_model_list = paginate.items
        total_page = paginate.pages
        current_page = paginate.page
        # 组装所需参数
        service_list_dict_li = []
        for service_list in service_list_model_list:
            service_list_dict = service_list.to_basic_dict()
            service_list_dict["goods_list"] = ""
            # 获取该工单的物品信息
            goods_obj_list = service_list.goods.all()

            if goods_obj_list:
                goods_name_list = []
                # 显示前三个物品
                for goods in goods_obj_list[:3]:
                    goods_name_list.append(goods.goods.name)
                service_list_dict["goods_list"] = "; ".join(goods_name_list)
            service_list_dict["approver"] = ""
            if service_list.service_status == SERVICE_STATUS["approve"]:
                # 当为审批状态时，查询当前审批人
                ins = WorkFlowAPiRequest(username=user.nickname)
                url = GET_SERVICE_LIAT_STATUS.format(service_list.tick_id)
                rstatus, resp = ins.getdata(method='get', url=url)
                print(rstatus)
                print(resp)
                if not rstatus:
                    service_list_dict["approver"] = ""
                else:
                    service_list_dict["approver"] = "(" + resp["data"]["participant_info_list"][0]["alias"] + ")"

            service_list_dict_li.append(service_list_dict)

        data = {
            "total_page" : total_page,
            "current_page" : current_page,
            "service_list_dict_li" : service_list_dict_li
        }
        return jsonify({"status" : 1, "data": data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@my_submit_blu.route("/info", methods=["GET"])
@user_login_data
def my_submit_info():
    """
    工单详细信息
    @return:
    """
    try:
        user = g.user
        # 获取参数
        service_list_id = request.args.get("service_list_id", None)
        # 2 校验
        if service_list_id is None:
            raise Exception("service_list_id缺失")
        # 3 查询工单数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")

        resp_data = {}
        # TODO 父工单留待日后
        # 组装所需参数
        resp_data["name"] = user.name
        resp_data["org"] = user.contacts.organization.name
        resp_data["title"] = service_list.title
        resp_data["service_item"] = service_list.service_item.name
        resp_data["price"] = round(float(service_list.price), 2) if service_list.price else 0
        resp_data["scope"] = scope_transition(service_list.scope)
        resp_data["urgency"] = urgency_transition(service_list.urgency)
        resp_data["descript"] = service_list.descript
        resp_data["service_status"] = 0
        if service_list.service_status == SERVICE_STATUS["grade"]:
            resp_data["service_status"] = 1
        elif service_list.service_status == SERVICE_STATUS["end"]:
            resp_data["service_status"] = 2
        # 获取工单下的物品
        goods_list = []
        goods_obj_list = service_list.goods.all()
        for each_goods in goods_obj_list:
            each_goods_dict = {}
            each_goods_dict["name"] = each_goods.goods.name
            each_goods_dict["qty"] = each_goods.qty
            goods_list.append(each_goods_dict)

        resp_data["goods_list"] = goods_list
        # 获取工单的委托人
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

        finish_list = [
            {"title": "发起" ,
             "person": user.name,
             "content": "已发起"
             }
        ]
        process_info = {}
        wait_list = []
        refuse_flag = True
        # 组装流程图所需参数
        if service_list.tick_id is not None:
            ins = WorkFlowAPiRequest(username=user.nickname)
            url = TICKET_STEPS.format(service_list.tick_id)
            rstatus, resp = ins.getdata(dict(per_page=10), method='get', url=url, )
            print(rstatus)
            print(resp)
            if not rstatus:
                raise Exception("获取处理步骤失败")
            value_list = resp["data"]["value"]
            value_list = value_list[1:-1]
            status = service_list.service_status
            if status == SERVICE_STATUS["approve"]:
                n = None
                for i in range(1, len(value_list)):
                    if len(value_list[i]["state_flow_log_list"]) == 0 and len(value_list[i-1]["state_flow_log_list"]) > 0:
                        # n = i-1
                        n = i
                        print("n", n)
                        break
                if n is None:
                    n = 0

                # finish_value_list = value_list[:n]
                # wait_value_list = value_list[n+1:]

                for index, each in enumerate(value_list):
                    if index < n:
                        each_dict = {}
                        each_dict["title"] = each["state_name"]
                        each_dict["person"] = ""
                        each_dict["content"] = ""
                        if len(each["state_flow_log_list"]) > 0:
                            each_dict["person"] = each["state_flow_log_list"][0]["participant_info"][
                                "participant_alias"]
                            each_dict["content"] = each["state_flow_log_list"][0]["transition"]["transition_name"]
                            if len(each["state_flow_log_list"][0]["suggestion"]) > 0:
                                each_dict["content"] = each["state_flow_log_list"][0]["transition"][
                                                           "transition_name"] + ":" + each["state_flow_log_list"][0]["suggestion"]
                        finish_list.append(each_dict)

                    elif index > n:
                        each_dict = {}
                        each_dict["title"] = each["state_name"]
                        each_dict["person"] = ""
                        each_dict["content"] = "待审批"
                        wait_list.append(each_dict)
                    else:
                        process_info["title"] = value_list[n]["state_name"]
                        process_info["person"] = ""
                        process_info["content"] = "待审批"

                wait_status_list = SERVICE_STATUS_LIST[1:]

                if SERVICE_STATUS["answer"] in wait_status_list and SERVICE_STATUS["run"] in wait_status_list:
                    wait_status_list.remove(SERVICE_STATUS["run"])

                for each in wait_status_list:
                    if each == SERVICE_STATUS["pause"]:
                        continue
                    each_dict = {}
                    each_dict["title"] = service_list_status_title_transition(each)
                    each_dict["content"] = service_list_status_transition(each)
                    if each == SERVICE_STATUS["allot"] or each == SERVICE_STATUS["closeing"]:
                        if service_list.agent is not None:
                            each_dict["person"] = service_list.agent.name
                        else:
                            each_dict["person"] = ""
                    if each == SERVICE_STATUS["answer"]:
                        each_dict["person"] = ""
                    if each == SERVICE_STATUS["grade"]:
                        each_dict["person"] = user.name
                    if each == SERVICE_STATUS["end"]:
                        each_dict["person"] = ""
                        each_dict["content"] = "未完成"
                    wait_list.append(each_dict)


            else:

                for each in value_list:
                    each_dict = {}
                    each_dict["title"] = each["state_name"]
                    each_dict["person"] = ""
                    each_dict["content"] = ""
                    if len(each["state_flow_log_list"]) > 0:
                        each_dict["person"] = each["state_flow_log_list"][0]["participant_info"]["participant_alias"]
                        each_dict["content"] = each["state_flow_log_list"][0]["transition"]["transition_name"]
                        if len(each["state_flow_log_list"][0]["suggestion"]) > 0:
                            each_dict["content"] = each["state_flow_log_list"][0]["transition"]["transition_name"] + ":" + each["state_flow_log_list"][0]["suggestion"]
                    finish_list.append(each_dict)
                    if len(each["state_flow_log_list"]) > 0 and each["state_flow_log_list"][0]["transition"]["transition_name"] != "同意":
                        refuse_flag = False
                        break
                if refuse_flag:
                    finish_status_list = SERVICE_STATUS_LIST[1:status - 1]
                    print(finish_status_list)
                    wait_status_list = []
                    if status != SERVICE_STATUS_LIST[-1]:
                        wait_status_list = SERVICE_STATUS_LIST[status:]

                    if SERVICE_STATUS["answer"] in finish_status_list and SERVICE_STATUS["run"] in finish_status_list:
                        finish_status_list.remove(SERVICE_STATUS["answer"])
                    if SERVICE_STATUS["answer"] in wait_status_list and SERVICE_STATUS["run"] in wait_status_list:
                        wait_status_list.remove(SERVICE_STATUS["run"])
                    if SERVICE_STATUS["answer"] in finish_status_list and SERVICE_STATUS["run"] == status:
                        finish_status_list.remove(SERVICE_STATUS["answer"])
                    if SERVICE_STATUS["run"] in wait_status_list and SERVICE_STATUS["answer"] == status:
                        wait_status_list.remove(SERVICE_STATUS["run"])

                    for each in finish_status_list:
                        if each == SERVICE_STATUS["pause"]:
                            continue
                        each_dict = {}
                        each_dict["title"] = service_list_status_title_transition(each)
                        if each == SERVICE_STATUS["allot"]:
                            each_dict["person"] = service_list.agent.name
                            each_dict["content"] = "已分配"
                        if each == SERVICE_STATUS["run"]:
                            each_dict["person"] = ""
                            each_dict["content"] = "执行完毕"
                        if each == SERVICE_STATUS["closeing"]:
                            each_dict["person"] = service_list.agent.name
                            each_dict["content"] = "已结案"
                        if each == SERVICE_STATUS["grade"]:
                            each_dict["person"] = user.name
                            each_dict["content"] = "已评分"
                        finish_list.append(each_dict)
                    for each in wait_status_list:
                        if each == SERVICE_STATUS["pause"]:
                            continue
                        each_dict = {}
                        each_dict["title"] = service_list_status_title_transition(each)
                        each_dict["content"] = service_list_status_transition(each)
                        if each == SERVICE_STATUS["allot"] or each == SERVICE_STATUS["closeing"]:
                            if service_list.agent is not None:
                                each_dict["person"] = service_list.agent.name
                            else:
                                each_dict["person"] = ""
                        if each == SERVICE_STATUS["answer"]:
                            each_dict["person"] = ""
                        if each == SERVICE_STATUS["grade"]:
                            each_dict["person"] = user.name
                        if each == SERVICE_STATUS["end"]:
                            each_dict["person"] = ""
                            each_dict["content"] = "未完成"
                        wait_list.append(each_dict)

                    process_info["title"] = service_list_status_title_transition(status)
                    process_info["person"] = ""
                    if status == SERVICE_STATUS["allot"]:
                        if service_list.agent is not None:
                            process_info["person"] = service_list.agent.name
                    if status == SERVICE_STATUS["closeing"]:
                        process_info["person"] = service_list.agent.name
                    if status == SERVICE_STATUS["grade"]:
                        process_info["person"] = user.name
                    process_info["content"] = service_list_status_transition(status)
                else:
                    if status != SERVICE_STATUS["end"]:
                        raise Exception("数据异常")

                    wait_list = [
                        {"title": "分配"},
                        {"title": "执行"},
                        {"title": "结案"},
                        {"title": "评分"},
                        {"title": "完成"}]
                    process_info = finish_list.pop(-1)

        else:
            status = service_list.service_status

            finish_status_list = SERVICE_STATUS_LIST[1:status-1]
            print(finish_status_list)
            wait_status_list = []
            if status != SERVICE_STATUS_LIST[-1]:
                wait_status_list = SERVICE_STATUS_LIST[status:]

            if SERVICE_STATUS["answer"] in finish_status_list and SERVICE_STATUS["run"] in finish_status_list:
                finish_status_list.remove(SERVICE_STATUS["answer"])
            if SERVICE_STATUS["answer"] in wait_status_list and SERVICE_STATUS["run"] in wait_status_list:
                wait_status_list.remove(SERVICE_STATUS["run"])
            if SERVICE_STATUS["answer"] in finish_status_list and SERVICE_STATUS["run"] == status:
                finish_status_list.remove(SERVICE_STATUS["answer"])
            if SERVICE_STATUS["run"] in wait_status_list and SERVICE_STATUS["answer"] == status:
                wait_status_list.remove(SERVICE_STATUS["run"])

            for each in finish_status_list:
                if each == SERVICE_STATUS["pause"]:
                    continue
                each_dict = {}
                each_dict["title"] = service_list_status_title_transition(each)
                if each == SERVICE_STATUS["allot"]:
                    each_dict["person"] = service_list.agent.name
                    each_dict["content"] = "已分配"
                if each == SERVICE_STATUS["run"]:
                    each_dict["person"] = ""
                    each_dict["content"] = "执行完毕"
                if each == SERVICE_STATUS["closeing"]:
                    each_dict["person"] = service_list.agent.name
                    each_dict["content"] = "已结案"
                if each == SERVICE_STATUS["grade"]:
                    each_dict["person"] = user.name
                    each_dict["content"] = "已评分"
                finish_list.append(each_dict)
            for each in wait_status_list:
                if each == SERVICE_STATUS["pause"]:
                    continue
                each_dict = {}
                each_dict["title"] = service_list_status_title_transition(each)
                each_dict["content"] = service_list_status_transition(each)
                if each == SERVICE_STATUS["allot"] or each == SERVICE_STATUS["closeing"]:
                    if service_list.agent is not None:
                        each_dict["person"] = service_list.agent.name
                    else:
                        each_dict["person"] = ""
                if each == SERVICE_STATUS["answer"]:
                    each_dict["person"] = ""
                if each == SERVICE_STATUS["grade"]:
                    each_dict["person"] = user.name
                if each == SERVICE_STATUS["end"]:
                    each_dict["person"] = ""
                    each_dict["content"] = "未完成"
                wait_list.append(each_dict)

            process_info["title"] = service_list_status_title_transition(status)
            process_info["person"] = ""
            if status == SERVICE_STATUS["allot"]:
                if service_list.agent is not None:
                    process_info["person"] = service_list.agent.name
            if status == SERVICE_STATUS["closeing"]:
                process_info["person"] = service_list.agent.name
            if status == SERVICE_STATUS["grade"]:
                process_info["person"] = user.name
            process_info["content"] = service_list_status_transition(status)

        resp_data["finish_list"] = finish_list
        resp_data["process_info"] = process_info
        resp_data["wait_list"] = wait_list
        resp_data["refuse_flag"] = refuse_flag

        # 获取工单执行人
        worker_list = []
        worker_obj_list = service_list.task_list.all()
        for each_worker in worker_obj_list:
            each_worker_dict = {}
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

        resp_data["worker_list"] = worker_list
        # 获取结案说明与解决方案
        resp_data["closeing_solution"] = ""
        resp_data["closeing_statment"] = ""
        if service_list.service_status in [SERVICE_STATUS["grade"], SERVICE_STATUS["end"]]:
            resp_data["closeing_solution"] = service_list.service_item_solution.name
            resp_data["closeing_statment"] = service_list.closeing_statment

        return jsonify({"status" : 1, "data": resp_data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})



@my_submit_blu.route("/add_mandator", methods=["POST"])
@user_login_data
def add_mandator():
    """
    添加委托人
    @return:
    """
    try:
        user = g.user
        # 获取参数
        data = request.json
        service_list_id = data.get("service_list_id", None)
        name = data.get("name", None)
        phone = data.get("phone", None)
        memo = data.get("memo", None)

        if not all([service_list_id, name, phone]):
            raise Exception("参数不全")

        #  查询工单数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该工单不存在")
        # 创建委托人对象
        service_list_contact = MDService_list_contact()
        service_list_contact.name = name
        service_list_contact.phone = phone
        service_list_contact.memo = memo
        service_list_contact.service_list = service_list
        service_list_contact.create_date = time.time()

        try:
            db.session.add(service_list_contact)
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存委托人失败")


        return jsonify({"status" : 1, "id": service_list_contact.id})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "添加委托人失败"})


@my_submit_blu.route("/delete_mandator", methods=["GET"])
@user_login_data
def delete_mandator():
    """删除委托人"""
    try:
        user = g.user
        # 获取参数
        id = request.args.get("id", None)
        print(id)

        if id is None:
            raise Exception("id参数缺失")

        #  查询委托人数据
        service_list_contact = MDService_list_contact.query.filter(MDService_list_contact.id == id).first()

        if not service_list_contact:
            raise Exception("该委托人不存在")

        try:
            # 删除
            db.session.delete(service_list_contact)
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("删除委托人失败")


        return jsonify({"status" : 1, "msg": "ok"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "删除委托人失败"})


@my_submit_blu.route("/get_image", methods=["GET"])
@user_login_data
def get_image():
    """
    获取附件
    @return:
    """
    try:
        user = g.user
        # 获取参数
        service_list_id = request.args.get("service_list_id", None)


        if service_list_id is None:
            raise Exception("service_list_id参数缺失")

        #  查询工单数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该服务单不存在")

        # 返回base64加密的图片数据列表
        image_list = []
        image_obj_list = service_list.attachment.filter(MDAttachment.use_num != 0).all()
        for each in image_obj_list:
            image_list.append(base64.b64encode(each.data).decode("utf-8"))

        return jsonify({"status" : 1, "image_list": image_list})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "获取附件失败"})


@my_submit_blu.route("/get_grade_info", methods=["GET"])
@user_login_data
def get_grade_info():
    """
    获取服务项评价分类信息
    @return:
    """
    try:
        user = g.user
        # 获取参数
        service_list_id = request.args.get("service_list_id", None)


        if service_list_id is None:
            raise Exception("service_list_id参数缺失")

        #  查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该服务单不存在")

        # 获取该工单的服务项目评价分类
        grade_list = []
        evaluate_obj_list = service_list.service_item.service_item_evaluate.all()

        if len(evaluate_obj_list) == 0:
            raise Exception("该服务单不存在服务项评价分类信息")

        for each in evaluate_obj_list:
            each_dict = {}
            each_dict["name"] = each.name
            each_dict["id"] = each.id
            grade_list.append(each_dict)

        return jsonify({"status" : 1, "grade_list": grade_list})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "获取服务项评价分类信息失败"})


@my_submit_blu.route("/grade", methods=["POST"])
@user_login_data
def grade():
    """评分"""
    try:
        user = g.user
        # 获取参数
        data = request.json
        service_list_id = data.get("service_list_id", None)
        score_list = data.get("score_list", None)

        if service_list_id is None:
            raise Exception("service_list_id参数缺失")
        if score_list is None:
            raise Exception("score_list参数缺失")

        #  查询数据
        service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

        if not service_list:
            raise Exception("该服务单不存在")

        this_time = time.time()
        new_evaluate_list = []
        for each in score_list:
            id = each["id"]
            score = each["score"]
            # 获取服务项评价信息对象
            evaluate_obj = MDService_Item_evaluate.query.filter(MDService_Item_evaluate.id == id,
                                                                MDService_Item_evaluate.service_item_id == service_list.service_item.id).first()
            if not evaluate_obj:
                raise Exception("服务项评价信息不存在")
            # 更新最高分与最低分
            if not evaluate_obj.highest:
                evaluate_obj.highest = score
            elif score > evaluate_obj.highest:
                evaluate_obj.highest = score
            if not evaluate_obj.lowest:
                evaluate_obj.lowest = score
            elif score < evaluate_obj.lowest:
                evaluate_obj.lowest = score
            # 获取服务单评价信息对象
            new_service_list_evaluate = MDService_list_evaluate.query.filter(MDService_list_evaluate.service_Item_evaluate_id == id, MDService_list_evaluate.service_list_id == service_list_id).first()
            if not new_service_list_evaluate:
                # 没有则新建
                new_service_list_evaluate = MDService_list_evaluate()
            new_service_list_evaluate.service_list_id = service_list_id
            new_service_list_evaluate.service_Item_evaluate_id = id
            new_service_list_evaluate.score = score
            new_service_list_evaluate.create_date = this_time
            new_service_list_evaluate.user_id = user.id
            new_evaluate_list.append(new_service_list_evaluate)
        # 更新工单状态
        service_list.service_status = SERVICE_STATUS["end"]

        try:
            # 保存
            db.session.add_all(new_evaluate_list)
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存评分信息失败")

        return jsonify({"status" : 1, "msg": "OK"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "评分失败"})