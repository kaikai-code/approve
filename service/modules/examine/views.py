import datetime
import requests
from . import examine_blu
import time
from flask.json import jsonify
from ... import db
from flask import request,g

from ...model.model import MDAttachment ,MDAttachmentView ,MDContacts,MDService_list ,MDGoods,MdService_Cluster

#
# @ examine_blu.route("/list",method=["get"])
# def my_examine():

