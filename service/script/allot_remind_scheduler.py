import hashlib
import time

import requests

from ..config.config import Config
from ..config.constants import REMIND_CRON
from ..utils.scheduler_utils import scheduler_task
from ..utils.logger_factory import logger
from .model import MDAttachment, MdService_Cluster, MDService, MDService_Type, MDService_Item, MDGoods, MDService_list, MDGoods, MDService_list_goods, MDService_list_contact, MDUSA_service_item, MDuser
from ..config.constants import PER_PAGE, SERVICE_LIST_TICK_ID_REDIS_EXPIRES, SERVICE_STATUS, CCP_APPROVE_NUMBER, REQUEST_RETRY_COUNT
from ..config.urls import MY_APPROVE, DISPOSE_TICKET, GET_TICKET_OPERATION, APPROVE_SERVICE_LIST, GET_SERVICE_LIAT_STATUS
import traceback
from service.libs.yuntongxun.sms import CCP
from retrying import retry


def allot_remind_scheduler():
    try:
        cron = REMIND_CRON
        scheduler_task.add_job(allot_remind, (), **cron)
    except Exception as e:
        print(traceback.format_exc())


def allot_remind():

    print(123123123123123)
    try:

        service_list_obj_list = MDService_list.query.filter(MDService_list.service_status == SERVICE_STATUS["approve"]).all()

        username_list = []
        for service_list in service_list_obj_list:
            try:
                result = request_approver(service_list.tick_id)
                print(result)
                code = result.get("code", -1)
                if code != 0:
                    print("Return result error")
                    continue

                participant_info_list = result["data"]["participant_info_list"]
                if len(participant_info_list) == 0:
                    continue
                username = participant_info_list[0].get("username")
                username_list.append(username)
            except:
                continue

        username_dict = {}
        for each_username in username_list:
            try:
                if each_username in username_dict:
                    username_dict[each_username] += 1
                else:
                    username_dict[each_username] = 1
            except:
                continue

        print(username_dict)

        for name, count in username_dict.items():
            try:
                user = MDuser.query.filter(MDuser.nickname == name).first()
                if not user:
                    continue
                mobile = user.contacts.phone
                result = CCP().send_template_sms(mobile, [count], CCP_APPROVE_NUMBER)
                if result != 0:
                    print("发送失败")
            except:
                continue

    except Exception as e:
        print(traceback.format_exc())


def getrequestheader():
    timestamp = str(time.time())[:10]
    ori_str = timestamp + Config.WORKFLOWTOKEN
    signature = hashlib.md5(ori_str.encode(encoding='utf-8')).hexdigest()
    headers = dict(signature=signature, timestamp=timestamp, appname=Config.WORKFLOWAPP)
    return headers

@retry(stop_max_attempt_number=REQUEST_RETRY_COUNT)
def request_approver(tick_id):

    url = Config.WORKFLOWBACKENDURL + GET_SERVICE_LIAT_STATUS.format(tick_id)
    headers = getrequestheader()

    resp = requests.get(url, headers=headers, timeout=3)
    if resp.status_code != 200:  # 状态码不是200，也会报错并充实
        print("request django error")
        raise Exception("request django error")
    result = resp.json()
    return result