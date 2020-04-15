import hashlib
import json
import time
import traceback

import requests
from ..config.config import Config


# WORKFLOWBACKENDURL = "http://192.168.111.129:8888/"
# WORKFLOWTOKEN = "30aa7f12-68fb-11ea-82e3-001a7dda7111"
# WORKFLOWAPP = "newworld"
#
#
# class WorkFlowAPiRequest(object):
#     def __init__(self, token=WORKFLOWTOKEN, appname=WORKFLOWAPP, username='li.xiaolan',
#                  workflowbackendurl=WORKFLOWBACKENDURL):
#         self.token = token
#         self.appname = appname
#
#         self.username = username
#         self.workflowbackendurl = workflowbackendurl
#
#     def getrequestheader(self):
#         timestamp = str(time.time())[:10]
#         ori_str = timestamp + self.token
#         signature = hashlib.md5(ori_str.encode(encoding='utf-8')).hexdigest()
#         headers = dict(signature=signature, timestamp=timestamp, appname=self.appname, username=self.username)
#         return headers

class WorkFlowAPiRequest(object):
    def __init__(self, username, token=Config.WORKFLOWTOKEN, appname=Config.WORKFLOWAPP,
                 workflowbackendurl=Config.WORKFLOWBACKENDURL):
        self.token = token
        self.appname = appname

        self.username = username
        self.workflowbackendurl = workflowbackendurl

    def getrequestheader(self):
        timestamp = str(time.time())[:10]
        ori_str = timestamp + self.token
        signature = hashlib.md5(ori_str.encode(encoding='utf-8')).hexdigest()
        headers = dict(signature=signature, timestamp=timestamp, appname=self.appname, username=self.username)
        return headers

    def getdata(self, parameters=dict(), method='', url='', timeout=300, data=dict()):
        if method not in ['get', 'post', 'put', 'delete', 'patch']:
            return False, 'method must be one of get post put delete or patch'
        if not isinstance(parameters, dict):
            return False, 'Parameters must be dict'
        headers = self.getrequestheader()
        try:
            # print(headers)
            r = getattr(requests, method)('{0}{1}'.format(self.workflowbackendurl, url), headers=headers,
                                          params=parameters, timeout=timeout, data=json.dumps(data))
            print(r)
            result = r.json()
            code = result.get("code", -1)
            if code != 0:
                return False, 'Return result error'
            return True, result
        except Exception as e:
            return False, traceback.format_exc()


if __name__ == '__main__':
    ins = WorkFlowAPiRequest()
    rstatus, resp = ins.getdata(dict(per_page=10), method='get', url='api/v1.0/workflows/1/init_state')
    print(rstatus)
    print(resp)
