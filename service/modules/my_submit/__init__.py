from flask import Blueprint

my_submit_blu = Blueprint("my_submit", __name__, url_prefix="/my_submit")


from . import views