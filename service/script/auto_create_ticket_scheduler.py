import datetime
import hashlib
import time

import requests

from ..config.config import Config
from ..config.constants import SUBMIT_CRON
from ..utils.scheduler_utils import scheduler_task
from ..utils.logger_factory import logger
from .model import MDAttachment, MdService_Cluster, MDService, MDService_Type, MDService_Item, MDGoods, MDService_list, MDGoods, MDService_list_goods, MDService_list_contact, MDUSA_service_item, MDuser, MDTiming_task, MDAllot_task, MDService_list_taskList
from ..config.constants import PER_PAGE, SERVICE_LIST_TICK_ID_REDIS_EXPIRES, SERVICE_STATUS, CCP_APPROVE_NUMBER, REQUEST_RETRY_COUNT, TASK_STATUS, SYSTEM_USER_ID
from ..config.urls import MY_APPROVE, DISPOSE_TICKET, GET_TICKET_OPERATION, APPROVE_SERVICE_LIST, GET_SERVICE_LIAT_STATUS
import traceback
from service.libs.yuntongxun.sms import CCP
from retrying import retry
from service.script.db_env import db


def auto_create_ticket_scheduler():
    try:
        # cron = SUBMIT_CRON
        # scheduler_task.add_job(auto_create_ticket, (), **cron)

        timing_task_obj_list = MDTiming_task.query.all()
        for timing_task in timing_task_obj_list:
            period = timing_task.period
            task_time = timing_task.task_time
            print(period)
            print(type(period))
            print(task_time)
            print(type(task_time))
            # task_time = datetime.datetime.now()
            hour = task_time.hour
            minute = task_time.minute
            second = task_time.second

            print(hour, type(hour))
            print(minute, type(minute))
            print(second, type(second))
            SUBMIT_CRON["day"] = "*/" + str(period)
            SUBMIT_CRON["hour"] = str(hour)
            SUBMIT_CRON["minute"] = str(minute)
            SUBMIT_CRON["second"] = str(second)
            print(SUBMIT_CRON)

            cron = SUBMIT_CRON
            scheduler_task.add_job(auto_create_ticket, (timing_task,), **cron)


    except Exception as e:
        print(traceback.format_exc())


def auto_create_ticket(timing_task):

    print(123123123123123)
    try:
        print(timing_task)
        this_time = time.time()
        service_list = MDService_list()

        service_list.title = timing_task.task_name
        service_list.source = 1
        service_list.descript = timing_task.descript
        service_list.scope = timing_task.scope
        service_list.urgency = timing_task.urgency
        service_list.user_id = SYSTEM_USER_ID
        service_list.create_date = this_time
        service_item = MDService_Item.query.filter(MDService_Item.id == timing_task.service_item_id,
                                                   MDService_Item.status == 1).first()
        if not service_item:
            print("服务项不存在")
            return
            # raise Exception("服务项不存在")

        usa_service_item = MDUSA_service_item.query.filter(
            MDUSA_service_item.service_Item_id == timing_task.service_item_id).first()
        if not usa_service_item:
            print("该服务项目没有对应的用户服务合同")
            return
            # raise Exception("该服务项目没有对应的用户服务合同")

        service_list.usa_service_item_id = usa_service_item.id

        service_list.service_item = service_item

        service_list.cost = timing_task.cost

        service_list.service_status = SERVICE_STATUS["allot"]

        db.session.add(service_list)

        allot_task_list = MDAllot_task.query.filter(MDAllot_task.timing_task_id == timing_task.id).all()
        if allot_task_list:
            service_list.service_status = SERVICE_STATUS["answer"]
            service_list.assign_date = this_time
        for allot_task in allot_task_list:

            service_list_task_list = MDService_list_taskList()
            service_list_task_list.service_list = service_list
            service_list_task_list.name = allot_task.plan_task_name
            service_list_task_list.descript = allot_task.descript
            service_list_task_list.worker_id = allot_task.user.id
            service_list_task_list.create_date = this_time
            service_list_task_list.status = TASK_STATUS["answer"]

            db.session.add(service_list_task_list)
        try:
            db.session.commit()
            print("成功")
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            print("保存工作任务表信息失败")
            # raise Exception("保存工作任务表信息失败")

    except Exception as e:
        print(traceback.format_exc())

