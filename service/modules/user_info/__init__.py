from flask import Blueprint

user_info_blu = Blueprint("user_info", __name__, url_prefix="/user")


from . import views