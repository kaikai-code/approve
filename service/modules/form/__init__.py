from flask import Blueprint

form_blu = Blueprint("form", __name__, url_prefix="/form")


from . import views