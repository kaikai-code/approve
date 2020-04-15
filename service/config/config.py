import logging
import os

CONFIG_NAME = os.environ.get("RUN_ENV", "DEV").upper()
if CONFIG_NAME not in ["DEV", "SIT", "UAT", "BETA", "PROD"]:
    CONFIG_NAME = "DEV"


class BaseConfig(object):
    """项目配置"""
    APP_NAME = "approve"

    LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.join(__file__, "../.."))), "logs")

    if not os.path.exists(LOG_PATH):
        os.mkdir(LOG_PATH)

    SECRET_KEY = "UdzEND+D+/IyfKBbBvbWnm9nhnOsorH+TVO+WZXCfHpfk7sN1psxHqniEG1M6HxT"

    # 为mysql添加配置
    SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://root:asd123!@@10.151.1.7:3306/approval"
    # SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://root:asd123!@@10.151.1.7:3306/user1"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    LOG_LEVEL = logging.DEBUG

    WX_LOGIN_URL = "https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code"

    # NEW_TICKET_URL = ""

    # OPENID = ["od3_n5U1SwGfDvbr8GWSo3uvhVP8"]

    # WORKFLOWBACKENDURL = "http://10.148.20.79:8000/"
    WORKFLOWBACKENDURL = "http://10.151.1.18:80/"
    WORKFLOWTOKEN = "30aa7f12-68fb-11ea-82e3-001a7dda7111"
    WORKFLOWAPP = "newworld"

    MISFIRE_GRACE_TIME = 300
    MAX_INSTANCES = 20


class DevConfig(BaseConfig):
    """开发环境"""
    DEBUG = True
    APP_ID = "wxed37e45c8e582d70"
    APP_SECRET = "b1ba7d405723352c379372a90f84fa6e"


class SitConfig(BaseConfig):
    """测试环境"""
    DEBUG = True


class UatConfig(BaseConfig):
    """测试环境"""
    DEBUG = True


class BetaConfig(BaseConfig):
    """测试环境"""
    DEBUG = True


class ProConfig(BaseConfig):
    """生产环境"""
    DEBUG = False
    LOG_LEVEL = logging.WARNING
    APP_ID = "wxed37e45c8e582d70"
    APP_SECRET = "b1ba7d405723352c379372a90f84fa6e"


config = {
    "DEV": DevConfig,
    "SIT": SitConfig,
    "UAT": UatConfig,
    "BETA": BetaConfig,
    "PROD": ProConfig
}

Config = config[CONFIG_NAME]
