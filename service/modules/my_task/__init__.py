from flask import Blueprint

my_task_blu = Blueprint("my_task", __name__, url_prefix="/my_task")


from . import views