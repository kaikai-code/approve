from flask import Blueprint

service_counter_blu = Blueprint("service_counter", __name__, url_prefix="/service_counter")


from . import views