from flask import Blueprint

my_approve_blu = Blueprint("my_approve", __name__, url_prefix="/my_approve")


from . import views