from flask import Blueprint

examine_blu = Blueprint("examine", __name__, url_prefix="/examine")


from . import views