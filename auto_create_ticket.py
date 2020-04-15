import os
import sys
PATH = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PATH)

# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# # from service import create_app
#
# from service.config.config import Config
#
# app = Flask(__name__)
# # 加载配置
# app.config.from_object(Config)
# db = SQLAlchemy(app)


if __name__ == '__main__':

    from service.utils.scheduler_utils import scheduler_task
    from service.script.auto_create_ticket_scheduler import auto_create_ticket_scheduler

    auto_create_ticket_scheduler()
    scheduler_task.start()