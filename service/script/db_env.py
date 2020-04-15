from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# from service import create_app

from service.config.config import Config

app = Flask(__name__)
# 加载配置
app.config.from_object(Config)
db = SQLAlchemy(app)
