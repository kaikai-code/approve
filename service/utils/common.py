#公用的自定义工具类
from flask import session, current_app, g, request


from ..model.model import MDuser
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from ..config.config import Config
from ..config.constants import TOKEN_EXPIRATION_TIME
from flask.json import jsonify


import functools

def user_login_data(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):

        token = request.headers.get("token")
        s = Serializer(Config.SECRET_KEY, TOKEN_EXPIRATION_TIME)
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            print(1)
            return jsonify({"status": 0, "msg": "请先登录"})
        user_id = data.get("user_id")
        openid = data.get("openid")
        try:
            user = MDuser.query.filter(MDuser.id == user_id,
                                   MDuser.wx_open_id == openid,
                                   MDuser.token == token).first()
        except:
            return jsonify({"status": 0, "msg": "请重新登陆"})
        if not user:
            print(2)
            return jsonify({"status": 0, "msg": "请先登录"})
        g.user = user
        return f(*args, **kwargs)
    return wrapper

def check_token(token):
    try:
        token = request.json.get("token")
        s = Serializer(Config.SECRET_KEY, TOKEN_EXPIRATION_TIME)

        data = s.loads(token.encode('utf-8'))

        user_id = data.get("user_id")
        openid = data.get("openid")

        user = MDuser.query.filter(MDuser.id == user_id,
                                   MDuser.wx_open_id == openid,
                                   MDuser.token == token).first()
        if not user:
            return False, None
        return True, user
    except Exception as e:
        return False, None




