import random
import re
import time

import requests
from flask import request, abort, current_app, make_response, jsonify, session
#
from ... import redis_store, db
from ...libs.yuntongxun.sms import CCP
from ...libs.captcha.captcha import captcha
# # from info.models import User
# # from info.utils.response_code import RET
from . import passport_blu
from ...model.model import MDUSA_org, MDuser, MDContacts
from ...config.constants import TOKEN_EXPIRATION_TIME, SMS_CODE_REDIS_EXPIRES, CCP_SMS_CODE_NUMBER
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from ...config.config import Config
from ...utils.logger_factory import logger


@passport_blu.route("/login", methods=["POST"])
def login():
    """
    登陆
    @return:
    """
    try:
        # 获取参数
        code = request.json.get("code", None)
        if not code:
            raise Exception("code缺失")
        print(code)
        # 获取openid
        url = Config.WX_LOGIN_URL.format(Config.APP_ID, Config.APP_SECRET, code)
        res = requests.get(url)
        if res.status_code != 200:
            raise Exception("微信登录失败")

        data = res.json()
        print(data)
        # {'session_key': 'HOloHjiF2weOHqpcNKib4w==', 'openid': 'od3_n5U1SwGfDvbr8GWSo3uvhVP8'}
        session_key = data.get("session_key", None)
        openid = data.get("openid", None)
        if not session_key or not openid:
            raise Exception("微信登录失败")
        # 查看该用户是否存在
        user = MDuser.query.filter(MDuser.wx_open_id == openid).first()

        if not user:
            # 不存在则新建
            user = MDuser(wx_session_id=session_key, wx_open_id=openid, create_date=time.time(), last_date=time.time(),
                          bind_status=0)
            try:
                db.session.add(user)
                db.session.commit()
            except Exception as e:
                logger.error(e)
                db.session.rollback()
                raise Exception("保存用户失败")
        if user.bind_status == 0:
            # 未绑定手机号
            return jsonify({"status": 2, "msg": "请先绑定手机号", "openid": openid, "user_id": user.id})
        # elif user.bind_status == 2:
        #     return jsonify({"status":3, "msg": "该用户不存在，请联系系统管理员", "openid":openid})
        else:
            #　签发token
            s = Serializer(Config.SECRET_KEY, TOKEN_EXPIRATION_TIME)
            token = s.dumps({"openid": openid, "user_id": user.id}).decode('utf-8')
            user.last_date = time.time()
            user.token = token
            try:
                #　成功则保存
                db.session.commit()
            except Exception as e:
                # 失败则回滚
                logger.error(e)
                db.session.rollback()
                raise Exception("更新用户信息失败")

        return jsonify({"status": 1, "token": token, "name": user.name})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@passport_blu.route("/check_login", methods=["POST"])
def check_login():
    """
    校验登陆状态
    @return:
    """
    try:
        # 获取token
        token = request.json.get("token")
        s = Serializer(Config.SECRET_KEY, TOKEN_EXPIRATION_TIME)
        try:
            # token解码
            data = s.loads(token.encode('utf-8'))
        except:
            return jsonify({"status": 0, "msg": "登陆过期"})
        else:
            user_id = data.get("user_id")
            openid = data.get("openid")

            user = MDuser.query.filter(MDuser.id == user_id, MDuser.wx_open_id == openid,
                                       MDuser.token == token).first()
            if not user:
                return jsonify({"status": 0, "msg": "登录失败"})
            return jsonify({"status": 1, "msg": "登录成功", "name": user.name})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@passport_blu.route("/register", methods=["POST"])
def register():
    """
    注册
    @return:
    """

    try:
        # 1 获取参数
        params_dict = request.json
        mobile = params_dict.get("mobile")
        name = params_dict.get("name")
        smscode = params_dict.get("smscode")
        openid = params_dict.get("openid")
        user_id = params_dict.get("user_id")

        # 2参数校验
        if not all([mobile, smscode, name, openid, user_id]):
            raise Exception("参数缺失")

        if not re.match(r"1[35678]\d{9}", mobile):
            raise Exception("手机号格式错误")
        pepeat_user = MDuser.query.filter(MDuser.nickname == name).first()
        if pepeat_user:
            return jsonify({"status": 6, "msg": "该用户名已被使用，请更换用户名"})
        # 3 从redis获取短信验证码
        try:
            real_sms_code = redis_store.get("SMS_" + mobile)
        except Exception as e:
            logger.error(e)
            raise Exception("数据查询失败")
        if not real_sms_code:
            return jsonify({"status": 2, "msg": "验证码已过期"})
        # 4
        if real_sms_code != smscode:
            return jsonify({"status": 3, "msg": "验证码输入错误"})

        user = MDuser.query.filter(MDuser.id == user_id).first()
        if not user:
            raise Exception("用户不存在")
        contacts = MDContacts.query.filter(MDContacts.phone == mobile).first()
        if not contacts:
            return jsonify({"status": 4, "msg": "该用户不存在，请联系系统管理员"})
        if contacts.bind_status == 1:
            return jsonify({"status": 5, "msg": "该手机已被绑定，请联系系统管理员"})

        # user与contacts绑定
        user.nickname = name
        user.name = contacts.name
        user.contacts = contacts
        user.bind_status = 1
        s = Serializer(Config.SECRET_KEY, TOKEN_EXPIRATION_TIME)
        token = s.dumps({"openid": openid, "user_id": user.id}).decode('utf-8')
        print(token)
        user.last_date = time.time()
        user.token = token

        contacts.last_date = time.time()
        contacts.bind_status = 1
        try:
            db.session.commit()
        except Exception as e:
            logger.error(e)
            db.session.rollback()
            raise Exception("更新用户信息失败")

        return jsonify({"status": 1, "msg": "绑定成功", "token": token, "name": user.name})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})


@passport_blu.route("/sms_code", methods=["POST"])
def send_sms_code():
    """
    发送短信验证码
    @return:
    """

    try:
        params_dict = request.json
        mobile = params_dict.get("mobile", None)
        if not mobile:
            raise Exception("mobile不能为空")
        if not re.match(r"1[35678]\d{9}", mobile):
            raise Exception("手机号格式错误")
        # 生成短信验证码
        sms_code_str = "%06d" % random.randint(0, 999999)
        logger.debug(sms_code_str)
        # 发送验证码
        print(mobile)
        SMS_CODE_REDIS_EXPIRE = int(SMS_CODE_REDIS_EXPIRES / 60)
        result = CCP().send_template_sms(mobile, [sms_code_str, SMS_CODE_REDIS_EXPIRE], CCP_SMS_CODE_NUMBER)
        if result != 0:
            raise Exception("短信验证码发送失败")
        # 将验证码存入redis
        try:
            redis_store.set("SMS_" + mobile, sms_code_str, SMS_CODE_REDIS_EXPIRES)
        except Exception as e:
            logger.error(e)
            raise Exception("验证码保存失败")
        return jsonify({"status": 1, "msg": "短信验证码发送成功"})
    except Exception as e:
        return jsonify({"status": 0, "msg": str(e)})
