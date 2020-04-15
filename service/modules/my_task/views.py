import base64
import datetime
import time

import requests
from flask.json import jsonify

from . import my_task_blu
from ... import redis_store, db
from flask import request, g
from ...model.model import MDAttachment, MdService_Cluster, MDService,\
    MDService_Type, MDService_Item, MDGoods, MDService_list, MDGoods,\
    MDService_list_goods, MDService_list_contact, MDUSA_service_item, \
    MDService_list_taskList
from ...utils.logger_factory import logger
from ...config.config import Config
from ...utils.common import user_login_data
from ...config.constants import PER_PAGE, SERVICE_STATUS, TASK_STATUS, CCP_GIVE_UP_TASK_NUMBER
import traceback

from ...utils.state_transition import urgency_transition, scope_transition, service_list_status_transition, service_list_task_status_transition
from ...utils.request_utils import WorkFlowAPiRequest
from ...config.urls import TICKET_STEPS
from ...libs.yuntongxun.sms import CCP


# @my_task_blu.route("/list", methods=["GET"])
# @user_login_data
# def my_task_list():
#
#     try:
#         user = g.user
#
#         task_obj_list = MDService_list_taskList.query.filter(MDService_list_taskList.worker_id == user.id).all()
#         all_service_list_id_list = [task_obj.service_list_id for task_obj in task_obj_list]
#         run_service_list_id_list = [task_obj.service_list_id for task_obj in task_obj_list if task_obj.status in [TASK_STATUS["answer"], TASK_STATUS["run"], TASK_STATUS["pause"]]]
#         end_service_list_id_list = [task_obj.service_list_id for task_obj in task_obj_list if task_obj.status == TASK_STATUS["end"]]
#         cancel_service_list_id_list = [task_obj.service_list_id for task_obj in task_obj_list if task_obj.status == TASK_STATUS["cancel"]]
#         reject_service_list_id_list = [task_obj.service_list_id for task_obj in task_obj_list if
#                                        task_obj.status == TASK_STATUS["reject"]]
#
#         print(all_service_list_id_list)
#         print(run_service_list_id_list)
#         print(end_service_list_id_list)
#
#         # 获取参数
#         status = request.args.get("status", None)
#         scope = request.args.get("scope", None)
#         urgency = request.args.get("urgency", None)
#         page = request.args.get("page", "1")
#         per_page = request.args.get("per_page", PER_PAGE)
#
#         #2 校验
#         try:
#             page = int(page)
#             per_page = int(per_page)
#         except Exception as e:
#             logger.error(e)
#             raise Exception("参数错误")
#         if not all([status, scope, urgency]):
#             raise Exception("参数缺失")
#         #3 查询数据
#         filters = []
#         if status != "all":
#             status = int(status)
#             if status == 1:
#                 filters.append(MDService_list.id.in_(run_service_list_id_list))
#             elif status == 2:
#                 filters.append(MDService_list.id.in_(end_service_list_id_list))
#             elif status == 3:
#                 filters.append(MDService_list.id.in_(cancel_service_list_id_list))
#             else:
#                 filters.append(MDService_list.id.in_(reject_service_list_id_list))
#         else:
#             filters.append(MDService_list.id.in_(all_service_list_id_list))
#
#         if scope != "all":
#             scope = int(scope)
#             filters.append(MDService_list.scope == scope)
#         if urgency != "all":
#             urgency = int(urgency)
#             filters.append(MDService_list.urgency == urgency)
#
#         try:
#             paginate = MDService_list.query.filter(*filters).order_by(MDService_list.create_date.desc()).paginate(page,per_page,False)
#         except Exception as e:
#             logger.error(e)
#             raise Exception("数据查询失败")
#         service_list_model_list = paginate.items
#         total_page = paginate.pages
#         current_page = paginate.page
#
#         service_list_dict_li = []
#         for service_list in service_list_model_list:
#             service_list_dict = service_list.to_basic_dict()
#             service_list_dict["goods_list"] = ""
#             goods_obj_list = service_list.goods.all()
#
#             if goods_obj_list:
#                 goods_name_list = []
#                 for goods in goods_obj_list[:3]:
#                     goods_name_list.append(goods.goods.name)
#                 service_list_dict["goods_list"] = "; ".join(goods_name_list)
#             service_list_dict_li.append(service_list_dict)
#
#         data = {
#             "total_page" : total_page,
#             "current_page" : current_page,
#             "service_list_dict_li" : service_list_dict_li
#         }
#         return jsonify({"status" : 1, "data": data})
#     except Exception as e:
#         print(traceback.format_exc())
#         return jsonify({"status": 0, "msg": "查询失败"})


@my_task_blu.route("/list", methods=["GET"])
@user_login_data
def my_task_list():

    try:
        user = g.user

        # task_obj_list = MDService_list_taskList.query.filter(MDService_list_taskList.worker_id == user.id).all()
        # run_task_obj_list = [task_obj for task_obj in task_obj_list if task_obj.status in [TASK_STATUS["answer"], TASK_STATUS["run"], TASK_STATUS["pause"]]]
        # end_task_obj_list = [task_obj for task_obj in task_obj_list if task_obj.status == TASK_STATUS["end"]]
        # cancel_task_obj_list = [task_obj for task_obj in task_obj_list if task_obj.status == TASK_STATUS["cancel"]]
        # reject_task_obj_list = [task_obj for task_obj in task_obj_list if
        #                                task_obj.status == TASK_STATUS["reject"]]

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
        filters = [MDService_list_taskList.worker_id == user.id]
        if status != "all":
            status = int(status)
            if status == 1:
                filters.append(MDService_list_taskList.status.in_([TASK_STATUS["answer"], TASK_STATUS["run"], TASK_STATUS["pause"]]))
            elif status == 2:
                filters.append(MDService_list_taskList.status == TASK_STATUS["end"])
            elif status == 3:
                filters.append(MDService_list_taskList.status == TASK_STATUS["cancel"])
            else:
                filters.append(MDService_list_taskList.status == TASK_STATUS["reject"])
        # else:
        #     filters.append(MDService_list.id.in_(all_service_list_id_list))

        if scope != "all":
            scope = int(scope)
            service_list_scope = MDService_list.query.filter(MDService_list.scope == scope).all()
            service_list_scope_id_list = [i.id for i in service_list_scope]

            filters.append(MDService_list_taskList.service_list_id.in_(service_list_scope_id_list))
        if urgency != "all":
            urgency = int(urgency)
            service_list_urgency = MDService_list.query.filter(MDService_list.urgency == urgency).all()
            service_list_urgency_id_list = [i.id for i in service_list_urgency]
            filters.append(MDService_list_taskList.service_list_id.in_(service_list_urgency_id_list))

        try:
            paginate = MDService_list_taskList.query.filter(*filters).order_by(MDService_list_taskList.create_date.desc()).paginate(page,per_page,False)
        except Exception as e:
            logger.error(e)
            raise Exception("数据查询失败")
        task_model_list = paginate.items
        total_page = paginate.pages
        current_page = paginate.page

        service_task_dict_li = []
        for task_model in task_model_list:
            task_dict = task_model.to_basic_dict()
            task_dict["goods_list"] = ""
            goods_obj_list = task_model.service_list.goods.all()

            if goods_obj_list:
                goods_name_list = []
                for goods in goods_obj_list[:3]:
                    goods_name_list.append(goods.goods.name)
                task_dict["goods_list"] = "; ".join(goods_name_list)
            service_task_dict_li.append(task_dict)

        data = {
            "total_page" : total_page,
            "current_page" : current_page,
            "service_task_dict_li" : service_task_dict_li
        }
        return jsonify({"status" : 1, "data": data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})

@my_task_blu.route("/info", methods=["GET"])
@user_login_data
def my_task_info():

    try:
        user = g.user
        # 获取参数
        service_task_id = request.args.get("service_task_id", None)
        # 2 校验
        if service_task_id is None:
            raise Exception("service_task_id缺失")
        # 3 查询数据
        service_list_task = MDService_list_taskList.query.filter(MDService_list_taskList.id == service_task_id).first()
        if not service_list_task:
            raise Exception("该任务单不存在")

        service_list = service_list_task.service_list

        if not service_list:
            raise Exception("该工单不存在")

        resp_data = {}
        # TODO 父工单留待日后
        resp_data["task_name"] = service_list_task.name
        resp_data["task_descript"] = service_list_task.descript
        # resp_data["name"] = user.name
        # resp_data["org"] = user.contacts.organization.name
        resp_data["name"] = service_list.user.name
        if service_list.user.contacts:
            resp_data["org"] = service_list.user.contacts.organization.name
        else:
            resp_data["org"] = "无"

        resp_data["service_list_id"] = service_list.id
        resp_data["title"] = service_list.title
        resp_data["service_item"] = service_list.service_item.name
        resp_data["price"] = round(float(service_list.price), 2) if service_list.price else 0
        resp_data["scope"] = scope_transition(service_list.scope)
        resp_data["urgency"] = urgency_transition(service_list.urgency)
        resp_data["descript"] = service_list.descript
        resp_data["service_status"] = service_list.service_status

        resp_data["service_task_status"] = service_list_task.status
        resp_data["status"] = service_list_task_status_transition(service_list_task.status)

        resp_data["closeing_statment"] = service_list_task.closeing_statment
        print(service_list_task.status)
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

        # ins = WorkFlowAPiRequest()
        # url = TICKET_STEPS.format(service_list.tick_id)
        # rstatus, resp = ins.getdata(dict(per_page=10), method='get', url=url, )
        # print(rstatus)
        # print(resp)
        # if not rstatus:
        #     raise Exception("获取处理步骤失败")

        return jsonify({"status" : 1, "data": resp_data})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "查询失败"})


@my_task_blu.route("/modify_status", methods=["GET"])
@user_login_data
def modify_status():

    try:
        user = g.user
        # 获取参数
        service_task_id = request.args.get("service_task_id", None)

        service_task_status = request.args.get("service_task_status", None)

        # 2 校验
        if service_task_id is None:
            raise Exception("service_task_id缺失")
        if service_task_status is None:
            raise Exception("service_task_status缺失")
        service_task_status = int(service_task_status)

        # 3 查询数据
        service_task_id = request.args.get("service_task_id", None)

        # 3 查询数据
        service_list_task = MDService_list_taskList.query.filter(MDService_list_taskList.id == service_task_id).first()
        if not service_list_task:
            raise Exception("该任务单不存在")

        service_list = service_list_task.service_list

        if not service_list:
            raise Exception("该工单不存在")

        this_time = time.time()
        if service_task_status == TASK_STATUS["run"]:
            service_list_task.status = TASK_STATUS["pause"]
            service_list_task.pause_date = this_time
        elif service_task_status == TASK_STATUS["pause"]:
            service_list_task.status = TASK_STATUS["run"]
            pause_date = service_list_task.pause_date
            cost_time = round(this_time - pause_date, 2)
            service_list_task.pause_time = service_list_task.pause_time + cost_time

        else:
            raise Exception("service_task_status异常")

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("更新工作任务表信息失败")

        service_task_status = service_list_task.status
        status = service_list_task_status_transition(service_list_task.status)

        return jsonify({"status" : 1, "service_task_status": service_task_status, "status_str": status})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "接受任务失败"})


@my_task_blu.route("/accept_task", methods=["GET"])
@user_login_data
def accept_task():

    try:
        user = g.user
        # 获取参数
        service_task_id = request.args.get("service_task_id", None)
        # 2 校验
        if service_task_id is None:
            raise Exception("service_task_id缺失")
        # 3 查询数据
        service_list_task = MDService_list_taskList.query.filter(MDService_list_taskList.id == service_task_id).first()
        if not service_list_task:
            raise Exception("该任务单不存在")

        service_list = service_list_task.service_list

        if not service_list:
            raise Exception("该工单不存在")

        this_time = time.time()
        service_list_task.response_date = this_time
        service_list_task.status = TASK_STATUS["run"]

        if service_list.service_status == SERVICE_STATUS["answer"]:
            service_list.service_status = SERVICE_STATUS["run"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("更新工作任务表信息失败")

        # service_status = service_list.service_status
        # status = service_list_status_transition(service_list.service_status)

        service_task_status = service_list_task.status
        status = service_list_task_status_transition(service_list_task.status)

        return jsonify({"status" : 1, "service_task_status": service_task_status, "status_str": status})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "接受任务失败"})


@my_task_blu.route("/give_up_task", methods=["GET"])
@user_login_data
def give_up_task():

    try:
        user = g.user
        # 获取参数
        service_task_id = request.args.get("service_task_id", None)
        # 2 校验
        if service_task_id is None:
            raise Exception("service_task_id缺失")
        # 3 查询数据
        service_list_task = MDService_list_taskList.query.filter(MDService_list_taskList.id == service_task_id).first()
        if not service_list_task:
            raise Exception("该任务单不存在")

        service_list = service_list_task.service_list

        if not service_list:
            raise Exception("该工单不存在")

        this_time = time.time()
        service_list_task.response_date = this_time
        service_list_task.close_date = this_time
        service_list_task.status = TASK_STATUS["cancel"]
        print(service_list.task_list.count())
        if service_list.task_list.filter(MDService_list_taskList.status.notin_([TASK_STATUS["cancel"], TASK_STATUS["reject"]])).count() == 1:
            service_list.service_status = SERVICE_STATUS["allot"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("更新工作任务表信息失败")

        # service_status = service_list.service_status
        # status = service_list_status_transition(service_list.service_status)

        service_task_status = service_list_task.status
        status = service_list_task_status_transition(service_list_task.status)
        # sms_code_str = "%06d" % random.randint(0, 999999)
        name = user.name
        title = service_list_task.name
        mobile = service_list.agent.contacts.phone
        print(mobile)
        result = CCP().send_template_sms(mobile, [name, title], CCP_GIVE_UP_TASK_NUMBER)
        if result != 0:
            # raise Exception("短信验证码发送失败")
            print("短信验证码发送失败")

        return jsonify({"status" : 1, "service_task_status": service_task_status, "status_str": status})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "放弃任务失败"})




@my_task_blu.route('/submit_task', methods=["POST"])
@user_login_data
def submit_task():

    try:
        user = g.user
        data = request.json

        # 服务单ID
        service_task_id = request.args.get("service_task_id", None)
        # 备注
        statment = data.get("remark_value", None)
        # 图片id
        image_id = data.get("image_id", None)

        print("service_task_id: ", service_task_id)
        print("statment: ", statment)
        print("image_id: ", image_id)


        if not all([service_task_id, statment, image_id]):
            raise Exception("参数不全")

        service_list_task = MDService_list_taskList.query.filter(MDService_list_taskList.id == service_task_id).first()
        if not service_list_task:
            raise Exception("该任务单不存在")

        service_list = service_list_task.service_list

        if not service_list:
            raise Exception("该工单不存在")

        for each_image in image_id:
            this_image = MDAttachment.query.filter(MDAttachment.id == each_image).first()
            if not this_image:
                raise Exception("附件不存在")

            this_image.task_attachment.append(service_list_task)
            this_image.use_num = this_image.use_num + 1
        this_time = time.time()
        service_list_task.close_date = this_time
        service_list_task.status = TASK_STATUS["end"]
        service_list_task.closeing_statment = statment
        other_service_list_task = service_list.task_list.filter(MDService_list_taskList.worker_id != user.id).all()
        closeing_flag = True
        for each in other_service_list_task:
            if each.status != TASK_STATUS["end"]:
                closeing_flag = False
        if closeing_flag:
            service_list.service_status = SERVICE_STATUS["closeing"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存提交信息失败")

        return jsonify({"status": 1, "msg": "提交成功"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "提交失败"})


@my_task_blu.route("/get_task_image", methods=["GET"])
@user_login_data
def get_task_image():

    try:
        user = g.user
        # 获取参数
        service_task_id = request.args.get("service_task_id", None)
        # 2 校验
        if service_task_id is None:
            raise Exception("service_task_id缺失")
        # 3 查询数据
        service_list_task = MDService_list_taskList.query.filter(MDService_list_taskList.id == service_task_id).first()
        if not service_list_task:
            raise Exception("该任务单不存在")

        service_list = service_list_task.service_list

        if not service_list:
            raise Exception("该工单不存在")


        image_list = []
        image_obj_list = service_list_task.attachment.filter(MDAttachment.use_num != 0).all()
        for each in image_obj_list:
            image_list.append(base64.b64encode(each.data).decode("utf-8"))

        return jsonify({"status" : 1, "task_image_list": image_list})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "获取附件失败"})