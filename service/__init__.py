
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# from flask_wtf import CSRFProtect
# from flask_wtf.csrf import generate_csrf
from redis import StrictRedis
from .config.config import Config
from .utils.logger_factory import logger
from flask_admin import Admin
from flask_babelex import Babel
import flask_login as login


db = SQLAlchemy()
redis_store = None # type: StrictRedis
admin = None


def create_app():
    # 配置日志
    app = Flask(__name__)

    # 加载配置
    app.config.from_object(Config)
    # 初始化数据库
    db.init_app(app)
    # admin = Admin(name='工单审批后台管理系统',index_view=MyAdminIndexView(), template_mode='bootstrap3')
    from service.modules.admin.login import MyAdminIndexView
    global admin
    admin = Admin(name='工单审批后台管理系统', index_view=MyAdminIndexView(), template_mode='bootstrap3')
    admin.init_app(app)
    babel = Babel(app)
    app.config['BABEL_DEFAULT_LOCALE'] = 'zh_CN'
    # 初始化 redis 存储对象
    global redis_store
    redis_store = StrictRedis(host=Config.REDIS_HOST,port=Config.REDIS_PORT,decode_responses=True)
    # 开启当前项目CSRF 保护
    # CSRFProtect(app)
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        from .model.model import SuperUser
        return db.session.query(SuperUser).get(user_id)
    # @app.after_request
    # def after_request(response):
    #     csrf_token = generate_csrf()
    #     response.set_cookie("csrf_token",csrf_token)
    #
    #     return response


    # 注册蓝图
    from .modules.passport import passport_blu
    app.register_blueprint(passport_blu)

    from .modules.form import form_blu
    app.register_blueprint(form_blu)

    from .modules.my_submit import my_submit_blu
    app.register_blueprint(my_submit_blu)

    from .modules.my_approve import my_approve_blu
    app.register_blueprint(my_approve_blu)

    from .modules.service_counter import service_counter_blu
    app.register_blueprint(service_counter_blu)

    from .modules.my_task import my_task_blu
    app.register_blueprint(my_task_blu)

    from .modules.user_info import user_info_blu
    app.register_blueprint(user_info_blu)

    return app