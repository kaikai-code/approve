import datetime
import time
import traceback

import requests
from flask.json import jsonify

from . import form_blu
from ... import redis_store, db
from flask import request, g
from ...model.model import MDAttachment, MdService_Cluster, MDService, MDService_Type, MDService_Item, MDGoods, \
    MDService_list, MDGoods, MDService_list_goods, MDService_list_contact, MDUSA_service_item, MDService_list_taskList
from ...utils.logger_factory import logger
from ...config.config import Config
from ...utils.common import user_login_data
from ...config.constants import AGGREMMENT_PARAM, SERVICE_STATUS, SERVICE_STATUS_LIST
from ...utils.request_utils import WorkFlowAPiRequest
from ...config.urls import NEW_TICKET, GET_NEW_TICKST_OPERATION


@form_blu.route('/submit', methods=["POST"])
@user_login_data
def form_submit():
    """
    提交
    @return:
    """
    try:
        user = g.user
        data = request.json
        # 父订单
        parents = data.get("parents", None)
        # 发起源
        source = data.get("source", 0)
        # 服务
        # service_and_item = data.get("service", None)
        # 服务项目
        service_item = data.get("service_item", None)
        # 描述
        descript = data.get("descript", None)
        # 影响范围
        scope = data.get("scope", None)
        # 紧急度
        urgency = data.get("urgency", None)
        # 物品信息
        goods = data.get("goods", None)
        # 总价
        price = data.get("price", 0)
        # 图片id
        image_id = data.get("image_id", None)
        # 图片id
        mandator_list = data.get("mandator_list", None)
        # transition_id
        transition_id = data.get("transition_id", None)

        print("parents: ", parents)
        print("source: ", source)
        print("descript: ", descript)
        print("scope: ", scope)
        print("urgency: ", urgency)
        print("goods: ", goods)
        print("price: ", price)
        print("image_id: ", image_id)
        print("mandator_list: ", mandator_list)
        print("transition_id: ", transition_id)
        print(type(transition_id))

        if not all([service_item, scope, urgency, image_id]):
            raise Exception("参数不全")

        scope = int(scope)
        urgency = int(urgency)
        service_item_id = int(service_item)
        # 新建工单
        service_list = MDService_list()
        if parents:
            parents = int(parents)
            service_list.parents_id = parents
        time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        title = "wx-" + time_str + ("%04d" % user.id)
        service_list.title = title
        service_list.source = source
        service_list.descript = descript
        service_list.scope = scope
        service_list.urgency = urgency
        service_list.user = user
        service_list.create_date = time.time()
        #　查询服务项目
        service_item = MDService_Item.query.filter(MDService_Item.id == service_item_id,
                                                   MDService_Item.status == 1).first()
        if not service_item:
            raise Exception("服务项不存在")
        #　查询usa_service_item
        usa_service_item = MDUSA_service_item.query.filter(
            MDUSA_service_item.service_Item_id == service_item_id).first()
        if not usa_service_item:
            raise Exception("该服务项目没有对应的用户服务合同")

        service_list.usa_service_item_id = usa_service_item.id

        service_list.service_item = service_item

        aggremment = scope * urgency
        print(aggremment)
        # 查询服务级别协议
        service_level_agreemnts_list = service_item.service_level_agreemnts.all()
        agg_count = len(service_level_agreemnts_list)
        if agg_count == 0:
            raise Exception("服务级别协议为空")
        print(agg_count)
        # agg_level_list = [i + 1 for i in range(AGGREMMENT_PARAM)]
        # 按照服务级别协议的个数分组
        agg_list = list_of_groups(AGGREMMENT_PARAM, agg_count)
        print(agg_list)
        agg_flag = False
        for index, value in enumerate(agg_list):
            #　aggremment在分组范围内
            if aggremment >= value[0] and aggremment <= value[1]:
                for i in service_level_agreemnts_list:
                    if i.key == (index + 1):
                        # 绑定服务级别协议
                        service_list.service_level_agreemnts = i
                        service_list.cost = i.cost
                        service_list.promise_tto = i.tto
                        service_list.promise_ttr = i.ttr
                        agg_flag = True
                        break
        if not agg_flag:
            raise Exception("服务级别协议匹配失败")
        db.session.add(service_list)
        real_price = 0
        all_count = 0
        goods_str = ""
        num = 0
        for each_goods in goods:
            goods_id = int(each_goods["name"])
            this_count = each_goods["count"]
            all_count += this_count
            # 判断物品是否存在
            this_goods = MDGoods.query.filter(MDGoods.id == goods_id).first()
            if not this_goods:
                raise Exception("该物品不存在")

            if num < 2:
                goods_str += this_goods.name
            if num < 1:
                goods_str += "、"
            # 新建商品对象
            this_service_list_goods = MDService_list_goods()
            this_service_list_goods.service_list = service_list
            this_service_list_goods.goods = this_goods
            this_service_list_goods.qty = this_count
            this_service_list_goods.user = user
            this_service_list_goods.goods_cost = (this_count * this_goods.cost)
            real_price += (this_count * this_goods.cost)
            db.session.add(this_service_list_goods)
            num += 1

        if real_price != price:
            raise Exception("总价异常")

        service_list.price = price
        for each_mandator in mandator_list:
            # 新建委托人对象
            this_mandator = MDService_list_contact()
            this_mandator.name = each_mandator["name"]
            this_mandator.phone = each_mandator["tel"]
            this_mandator.memo = each_mandator["remark"]
            this_mandator.create_date = time.time()
            this_mandator.service_list = service_list
            db.session.add(this_mandator)

        for each_image in image_id:
            this_image = MDAttachment.query.filter(MDAttachment.id == each_image).first()
            if not this_image:
                raise Exception("附件不存在")
            # 绑定附件
            this_image.service_list_attachment.append(service_list)
            this_image.use_num = this_image.use_num + 1

        workflow_id = service_item.workerflow_id
        if workflow_id is not None and workflow_id != "" and transition_id is not None:
            #如果workflow_id存在则需要审批
            service_list.service_status = SERVICE_STATUS["approve"]
            data_title = user.name + "-" + service_item.name
            if len(goods_str) > 0:
                data_title = data_title + "-" + goods_str

            data = {
                "workflow_id": workflow_id,
                "transition_id": transition_id,
                "title": data_title,
                "txt": descript,
                "qty": all_count,
                # "dept_level": user.contacts.dept_level,
                "dept_level": 5,
                "cost": round(price, 2)

            }
            # 访问django创建工单
            ins = WorkFlowAPiRequest(username=user.nickname)

            rstatus, resp = ins.getdata(method='post', url=NEW_TICKET, data=data)
            print(rstatus)
            print(resp)
            if not rstatus:
                raise Exception("获取单号失败")
            ticket_id = resp["data"]["ticket_id"]
            print("ticket_id", ticket_id)
            service_list.tick_id = ticket_id
        else:
            # 没有审批流程
            service_list.service_status = SERVICE_STATUS["allot"]

        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存单据信息失败")

        return jsonify({"status": 1, "msg": "提交成功"})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": 0, "msg": "提交失败"})


def list_of_groups(all_count, per_list_len):
    '''
    匹配协议级别
    :param all_count:   12
    :param per_list_len:  每个小列表的长度
    :return:
    '''
    num = all_count / per_list_len
    end_list = []
    start_num = 1
    end_num = num
    while True:
        if start_num > all_count:
            break
        end_list.append([start_num, end_num])
        start_num = end_num + 0.00001
        end_num += num
    return end_list


@form_blu.route('/image', methods=["POST"])
@user_login_data
def form_image():
    """
    提交图片（附件）
    @return:
    """
    try:
        user = g.user
        #　获取图片
        image = request.files["image"].read()
        name = request.form.get("name", "")

        if image is None:
            raise Exception("image异常")
        if not name:
            raise Exception("name异常")

        if name == "task":
            # 此处为任务单附件
            service_list_id = request.form.get("service_list_id", None)
            if service_list_id is None:
                raise Exception("service_list_id不能为空")

            service_list = MDService_list.query.filter(MDService_list.id == service_list_id).first()

            if not service_list:
                raise Exception("该工单不存在")
            name = service_list.title
        #　获取图片大小
        length = len(image)

        date = time.time()
        # 新建图片对象
        attachment = MDAttachment(name=name, data=image, length=length,
                                  use_num=0, create_date=date, user_id=user.id)

        try:
            db.session.add(attachment)
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("保存图片失败")

        return jsonify({"status": 1, "id": attachment.id})
    except Exception as e:
        print(str(e))
        return jsonify({"status": 0, "msg": "保存图片失败"})

@form_blu.route('/service', methods=["GET"])
@user_login_data
def service():
    try:
        user = g.user
        # 获取所有服务
        service_obj_list = MDService.query.filter(MDService.status == 1).all()
        if not service:
            raise Exception("服务不存在")

        # 组装出参
        result_list = []
        for each in service_obj_list:
            each_dict = {}
            each_dict["name"] = each.name
            each_dict["id"] = each.id
            result_list.append(each_dict)

        return jsonify({"status": 1, "service": result_list})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@form_blu.route('/service_info', methods=["GET"])
@user_login_data
def get_service():
    """
    获取服务项目
    @return:
    """
    try:
        user = g.user
        # 获取入参
        service_id = request.args.get("service_id", None)

        print("service_id", service_id)
        # 校验
        if service_id is None:
            raise Exception("service_id不能为空")
        # 获取该服务
        service = MDService.query.filter(MDService.id == service_id,
                                         MDService.status == 1).first()
        if not service:
            raise Exception("该服务不存在")
        # print(service.name)
        title = service.name
        # 获取该用户的所有用户服务合同
        usa_service_contract_list = user.contacts.organization.USA_service_contract.all()
        # 获取该用户的欧诺个户服务合同所支持的服务项目
        serice_item_id_list = []
        for each_usa_service_contract in usa_service_contract_list:
            serice_item_list = each_usa_service_contract.service_item.all()
            for each_serice_item in serice_item_list:
                serice_item_id_list.append(each_serice_item.id)
        print("serice_item_id_list", serice_item_id_list)
        # 筛选出符合的服务项目
        serice_item = service.service_item.filter(MDService_Item.status == 1,
                                                  MDService_Item.id.in_(serice_item_id_list)).all()
        print(serice_item)
        if not serice_item:
            #　服务项目为空
            return jsonify({"status": 2})
        result_list = []
        for each in serice_item:
            each_dict = {}
            each_dict["title"] = each.name
            each_dict["value"] = str(each.id)
            result_list.append(each_dict)
        # 查询该用户所有未完成工单
        serice_list_obj_list = MDService_list.query.filter(MDService_list.user_id == user.id,
                                                           MDService_list.service_status.in_(
                                                               SERVICE_STATUS_LIST[:6])).order_by(
            MDService_list.create_date.desc()).all()
        # 组装父工单信息
        father_list = []
        for each in serice_list_obj_list:
            each_dict = {}
            each_dict["title"] = each.title
            each_dict["value"] = str(each.id)
            father_list.append(each_dict)

        return jsonify({"status": 1,"title":title, "service_item_list": result_list, "father_list": father_list})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


# @form_blu.route('/service_item', methods=["GET"])
# @user_login_data
# def get_service_item():
#     """
#
#     @return:
#     """
#     try:
#         user = g.user
#         service_id = request.args.get("service_id", None)
#
#         print("service_id", service_id)
#         if service_id is None:
#             raise Exception("service_id不能为空")
#         service = MDService.query.filter(MDService.id == service_id, MDService.status == 1).first()
#         if not service:
#             raise Exception("service_id不存在")
#         # print(service.name)
#
#         usa_service_contract_list = user.contacts.organization.USA_service_contract.all()
#
#         serice_item_id_list = []
#         for each_usa_service_contract in usa_service_contract_list:
#             serice_item_list = each_usa_service_contract.service_item.all()
#             for each_serice_item in serice_item_list:
#                 serice_item_id_list.append(each_serice_item.id)
#         print("serice_item_id_list", serice_item_id_list)
#
#         serice_item = service.service_item.filter(MDService_Item.status == 1,
#                                                   MDService_Item.id.in_(serice_item_id_list)).all()
#         print(serice_item)
#         # if not serice_item:
#         #     raise Exception("该服务没有对应的服务存在")
#         result_list = []
#         for each in serice_item:
#             each_dict = {}
#             each_dict["label"] = each.name
#             each_dict["value"] = each.id
#             result_list.append(each_dict)
#         return jsonify({"status": 1, "service_item_list": result_list})
#     except Exception as e:
#         return jsonify({"status": 0, "msg": str(e)})


@form_blu.route('/goods', methods=["GET"])
@user_login_data
def get_goods():
    """
    获取物品信息

    @return:
    """
    try:
        user = g.user
        # 获取入参
        service_item_id = request.args.get("service_item_id", None)

        print("service_item_id", service_item_id)
        if service_item_id is None:
            raise Exception("service_item_id不能为空")
        # 获取服务项目
        service_item = MDService_Item.query.filter(MDService_Item.id == service_item_id,
                                                   MDService_Item.status == 1).first()
        if not service_item:
            raise Exception("service_id不存在")
        # print(service.name)
        # 获取该工单的可执行transition_id
        if not service_item.workerflow_id:
            transition_id = None
        else:
            ins = WorkFlowAPiRequest(username=user.nickname)
            url = GET_NEW_TICKST_OPERATION.format(service_item.workerflow_id)
            print("service_item.workerflow_id", service_item.workerflow_id)
            rstatus, resp = ins.getdata(method='get', url=url)
            print(rstatus)
            print(resp)
            if not rstatus:
                raise Exception("获取服务项目信息失败")
            transition_list = resp["data"]["transition"]
            if len(transition_list) != 1:
                raise Exception("获取服务项目信息失败")
            transition_id = transition_list[0]["transition_id"]
        # 获取该工单的商品
        goods = service_item.goods.all()
        print(goods)
        # 组装出参参
        result_list = []
        price_dict = {}
        name_dict = {}
        for each in goods:
            each_dict = {}
            each_dict["title"] = each.name
            each_dict["value"] = str(each.id)
            result_list.append(each_dict)
            price_dict[str(each.id)] = float(each.cost)
            name_dict[str(each.id)] = each.name
        return jsonify({"status": 1, "goods_list": result_list,
                        "price_dict": price_dict, "name_dict": name_dict, "transition_id": transition_id})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})




# @form_blu.route('/base_info', methods=["GET"])
# def get_base_info():
#
#     try:
#         service_cluster_id = request.args.get("service_cluster_id", None)
#
#         print("service_cluster_id", service_cluster_id)
#         if service_cluster_id is None:
#             raise Exception("service_cluster_id不能为空")
#         service_cluster = MdService_Cluster.query.filter(MdService_Cluster.id == service_cluster_id, MdService_Cluster.status == 0).first()
#         if not service_cluster:
#             raise Exception("service_cluster_id不存在")
#         # print(service.name)
#
#         serice = service_cluster.service.all()
#         print(serice)
#         if not serice:
#             raise Exception("该服务簇没有对应的服务存在")
#         return "hehe"
#     except Exception as e:
#         return jsonify({"status": 0, "msg": str(e)})
