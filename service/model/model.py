import time
from datetime import datetime

from flask import url_for, request
from flask_admin.menu import MenuLink
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect
from wtforms.validators import required

from .. import db, admin
from flask_admin.contrib.sqla import ModelView
from ..utils.state_transition import urgency_transition, service_list_status_transition, service_list_task_status_transition
import flask_login as login



STATUS = {"Disable": 0, "Enable": 1}  # 记录状态
BILLING_CYCLE_UNIT = {"day": 0, "week": 1, "month": 2, "year": 3}  # 计费周期
SERVER_SOURCE = {"wx_app": 0, "app": 1, "help_desk": 2}  # 服务单发起来源
SCOPE = {"single": 1, "area": 2, "all": 3}  # 影响范围 (个体、区域、整体)
URGENCY = {"low": 1, "mid": 2, "high": 3, "highest": 4}  # 紧急度 (低、中、高、非常高)
SERVICE_STATUS = {"cancel": 0, "apply": 1, "wait_response": 2,
                  "doing": 3, "suspend": 4, "close": 5}  # 服务单状态（取消、申请、待响应、进行中、暂停、完成）
TASK_STATUS = {"cancel": 0, "wait_response": 1, "doing": 2,
               "suspend": 3, "close": 4}  # 服务单状态（取消、待响应、进行中、暂停、完成）1,2,3,4,5


class BaseView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access

        return redirect(url_for('admin.login_view', next=request.url))



# 附件表
#
class MDAttachment(db.Model):
    __tablename__ = 'Attachment'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(100))  # 附件文件名
    data = db.Column(db.LargeBinary(16777216))  # 附件内容
    length = db.Column(db.Integer)  # 附件大小（字节）
    use_num = db.Column(db.Integer)  # 被引用计数

    create_date = db.Column(db.Integer)  # 建立日期
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"))  # 上传者ID（外键）

    task_attachment = db.relationship("MDService_list_taskList",
                                      secondary="Task_attachment",
                                      lazy="dynamic",
                                      backref=db.backref('attachment', lazy='dynamic'))

    service_list_attachment = db.relationship("MDService_list",
                                              secondary="Service_list_attachment",
                                              lazy="dynamic",
                                              backref=db.backref('attachment', lazy='dynamic'))

    service_contract_attachment = db.relationship("MDService_contract",
                                                  secondary="Service_contract_attachment",
                                                  lazy="dynamic",
                                                  backref=db.backref('attachment', lazy='dynamic'))

    def __str__(self):
        return self.name


# 物品表
#
class MDGoods(db.Model):
    __tablename__ = 'Goods'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(100))  # 物品名称
    goods_type = db.Column(db.String(50))  # 物品分类
    cost = db.Column(db.Numeric(10, 2))  # 费用
    create_date = db.Column(db.Integer)  # 建立日期
    last_date = db.Column(db.Integer)  # 最后更新

    service_list_goods = db.relationship('MDService_list_goods', backref='goods',
                                         lazy='dynamic')

    service_item = db.relationship("MDService_Item",
                                   secondary="service_item_goods",
                                   lazy="dynamic",
                                   backref=db.backref('goods', lazy='dynamic'))
    def __str__(self):
        return self.name


class MDService_Item_Goods(db.Model):
    __tablename__ = 'service_item_goods'

    service_item_id = db.Column(db.Integer, db.ForeignKey(
        "Service_Item.id"), primary_key=True)  # 服务项目ID（外键）
    goods_id = db.Column(db.Integer, db.ForeignKey(
        "Goods.id"), primary_key=True)  # 商品ID（外键）


# ------------------------------------------------服务管理---------------------------------------------------------
# 服务簇
#
class MdService_Cluster(db.Model):
    __tablename__ = 'Service_Cluster'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(50))  # 服务簇名称
    status = db.Column(db.Integer, default=1)  # 状态
    service = db.relationship('MDService', backref='service_cluster',
                              lazy='dynamic')
    def __str__(self):
        return self.name

    @property
    def status_str(self):
        if self.status == 0:
            return "无效"
        else:
            return "生效"

class MdService_ClusterView(BaseView):
    column_labels = dict(name='服务簇名称', status='状态', status_str="状态")
    column_list = ['name', 'status_str']
    # column_exclude_list = ['data', ]
    # column_searchable_list = ['name', 'length']
    # column_filters = ['use_num']
    # column_editable_list = ['name', ]
    form_excluded_columns = ['service']
    form_choices = {
        'status': [("0", "无效"), ("1", "生效")]
    }
    form_args = {
        'name': {
            'label': '服务簇名称',
            'validators': [required()]
        },
        'status': {'label': "状态",'validators': [required()]}

    }
    # create_modal = True
    # edit_modal = True
    # can_view_details = True
    # form_ajax_refs = {
    #     'service': {
    #         'fields': ['name'],
    #         'page_size': 5
    #     }
    # }



# 服务
#
class MDService(db.Model):
    __tablename__ = 'Service'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    Service_cluster_id = db.Column(db.Integer, db.ForeignKey("Service_Cluster.id"))  # 服务簇ID(外键)
    name = db.Column(db.String(50))  # 服务名称
    memo = db.Column(db.String(100))  # 备注
    status = db.Column(db.Integer, default=1)  # 状态
    service_item = db.relationship('MDService_Item', backref='service',
                                   lazy='dynamic')
    def __str__(self):
        return self.name

    @property
    def status_str(self):
        if self.status == 0:
            return "无效"
        else:
            return "生效"

class MDServiceView(BaseView):
    column_labels = dict(name='服务名称', status='状态', status_str="状态", memo="备注", service_cluster="服务簇名称")
    column_list = ['name', 'service_cluster', 'memo', 'status_str']
    # column_exclude_list = ['data', ]
    # column_searchable_list = ['name', 'length']
    # column_filters = ['use_num']
    # column_editable_list = ['name', ]
    form_excluded_columns = ['service_item']
    form_choices = {
        'status': [("0", "无效"), ("1", "生效")]
    }
    form_args = {
        'name': {
            'label': '服务名称',
            'validators': [required()]
        },
        'status': {'label': "状态",'validators': [required()]},
        'service_cluster': {'label': "服务簇",'validators': [required()]},
        'memo': {'label': "备注"},

    }


# 服务项目类型
#
class MDService_Type(db.Model):
    __tablename__ = 'Service_Type'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(50))  # 服务项目类型名称
    code = db.Column(db.String(20))  # 服务项目类型代码
    memo = db.Column(db.String(100))  # 备注
    status = db.Column(db.Integer)  # 状态
    service_item = db.relationship('MDService_Item',
                                   backref='service_type', lazy='dynamic')
    def __str__(self):
        return self.name


# 服务项目
#
class MDService_Item(db.Model):
    __tablename__ = 'Service_Item'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    service_id = db.Column(db.Integer, db.ForeignKey("Service.id"))  # 服务ID（外键）
    contract_id = db.Column(db.Integer, db.ForeignKey("Service_contract.id"))  # #服务合约ID（外键）
    service_type_id = db.Column(db.Integer, db.ForeignKey("Service_Type.id"))  # #服务项目类型ID（外键）
    name = db.Column(db.String(50))  # 服务项目名称
    memo = db.Column(db.String(100))  # 备注
    status = db.Column(db.Integer)  # 状态

    workerflow_id = db.Column(db.Integer) # 工作流ID

    service_item_agent = db.relationship('MDService_Item_agent',
                                         backref='service_item', lazy='dynamic')
    service_item_evaluate = db.relationship('MDService_Item_evaluate',
                                            backref='service_item', lazy='dynamic')
    service_item_solution = db.relationship('MDService_Item_solution',
                                            backref='service_item', lazy='dynamic')
    service_level_agreemnts = db.relationship('MDService_level_agreements',
                                              backref='service_item', lazy='dynamic')
    service_list = db.relationship('MDService_list',
                                   backref='service_item', lazy='dynamic')
    timing_task = db.relationship('MDTiming_task',
                                   backref='service_item', lazy='dynamic')

    def __str__(self):
        return self.name



# 服务项目代理人表（服务台）
#
class MDService_Item_agent(db.Model):
    __tablename__ = 'Service_Item_agent'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    service_Item_id = db.Column(db.Integer, db.ForeignKey("Service_Item.id"))  # 服务项目ID（外键）
    user_id = db.Column(db.Integer, db.ForeignKey("User.id", ondelete="NO ACTION"))  # 服务台用户ID（外键）
    memo = db.Column(db.String(100))  # 备注
    create_date = db.Column(db.Integer)  # 建立日期
    status = db.Column(db.Integer)  # 状态



# 服务项评价分类表
#
class MDService_Item_evaluate(db.Model):
    __tablename__ = 'Service_Item_evaluate'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    service_item_id = db.Column(db.Integer, db.ForeignKey("Service_Item.id"))  # 服务项目ID（外键）
    name = db.Column(db.String(50))  # 服务项目评价名称
    highest = db.Column(db.Float)  # 最高分
    lowest = db.Column(db.Float)  # 最低分

    service_list_evaluate = db.relationship('MDService_list_evaluate',
                                            backref='service_item_evaluate', lazy='dynamic')

    def __str__(self):
        return self.name

# 服务项解决方案表
#
class MDService_Item_solution(db.Model):
    __tablename__ = 'Service_Item_solution'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    service_item_id = db.Column(db.Integer, db.ForeignKey("Service_Item.id"))  # 服务项目ID（外键）
    name = db.Column(db.String(50))  # 解决方案名称
    memo = db.Column(db.String(100))  # 备注
    status = db.Column(db.Integer)  # 状态

    service_list = db.relationship('MDService_list',
                                   backref='service_item_solution', lazy='dynamic')
    def __str__(self):
        return self.name


# 服务级别协议表
#
class MDService_level_agreements(db.Model):
    __tablename__ = 'Service_level_agreemnts'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    service_item_id = db.Column(db.Integer, db.ForeignKey("Service_Item.id"))  # 服务项目ID（外键）
    key = db.Column(db.Integer) # 服务级别协议key 1,2,3,4...
    name = db.Column(db.String(50))  # 服务级别协议名称
    cost = db.Column(db.Numeric(10, 2))  # 服务费
    tto = db.Column(db.Integer)  # 响应时间
    ttr = db.Column(db.Integer)  # 解决时间
    status = db.Column(db.Integer)  # 状态
    last_date = db.Column(db.Integer)  # 信息最后更新日期

    service_list = db.relationship('MDService_list',
                                   backref='service_level_agreemnts', lazy='dynamic')
    def __str__(self):
        return self.name


# 服务参数表（基础信息表）
#
class MDService_level_params(db.Model):
    __tablename__ = 'Service_level_params'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(50))  # 服务项目评价名称
    tto = db.Column(db.Integer)  # 响应时间
    ttr = db.Column(db.Integer)  # 解决时间
    status = db.Column(db.Integer)  # 状态
    def __str__(self):
        return self.name

# 服务供应商表
#
class MDService_vendor(db.Model):  # 一对一按那个键对应
    __tablename__ = 'Service_vendor'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(50))  # 供应商名称
    contacts = db.Column(db.String(50))  # 联系人
    contactus = db.Column(db.String(100))  # 联系方式
    address = db.Column(db.String(50))  # 地址
    legal_representative = db.Column(db.String(50))  # 法人代表
    enterprise_code = db.Column(db.String(50))  # 企业代码
    memo = db.Column(db.String(100))  # 备注
    status = db.Column(db.Integer)  # 状态
    service_org = db.Column(db.Integer)  # 服务团队架构
    last_date = db.Column(db.Integer)  # 信息最后更新日期

    org_id = db.Column(db.Integer, db.ForeignKey("Organization.id"))  # 组织结构ID（外键）

    service_contract = db.relationship('MDService_contract',
                                       backref='service_vendor', lazy='dynamic')
    def __str__(self):
        return self.name

# 服务合同
#
class MDService_contract(db.Model):
    __tablename__ = 'Service_contract'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(50))  # 合同名称
    service_vendor_id = db.Column(db.Integer, db.ForeignKey("Service_vendor.id"))  # 服务供应商ID（外键）
    valid_date = db.Column(db.Integer)  # 有效日期
    billing_cycle = db.Column(db.Integer)  # 计费周期
    billing_cycle_unit = db.Column(db.Integer)  # 计费周期单位
    currency = db.Column(db.String(10))  # 币种
    memo = db.Column(db.String(100))  # 备注
    status = db.Column(db.Integer)  # 状态

    service_item = db.relationship('MDService_Item',
                                   backref='service_contract', lazy='dynamic')
    def __str__(self):
        return self.name
# 服务合同附件
#
class MDService_contract_attachment(db.Model):
    __tablename__ = 'Service_contract_attachment'

    service_contract_id = db.Column(db.Integer, db.ForeignKey(
        "Service_contract.id"), primary_key=True)  # 服务合同ID（外键）
    attachment_id = db.Column(db.Integer, db.ForeignKey(
        "Attachment.id"), primary_key=True)  # 附件ID（外键）



# 用户服务合同
#
class MDUSA_service_contract(db.Model):
    __tablename__ = 'USA_service_contract'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(50))  # 用户服务合同名称
    start_date = db.Column(db.Integer)  # 开始日期
    end_date = db.Column(db.Integer)  # 结束日期
    memo = db.Column(db.String(100))  # 备注
    status = db.Column(db.Integer)  # 状态

    service_item = db.relationship("MDService_Item",
                                   secondary="USA_service_item",
                                   lazy="dynamic",
                                   backref=db.backref('USA_service_contract', lazy='dynamic'))

    organization = db.relationship("MDOrganization",
                                   secondary="USA_org",
                                   lazy="dynamic",
                                   backref=db.backref('USA_service_contract', lazy='dynamic'))
    def __str__(self):
        return self.name

# USA合同-服务项（N-N交叉表）
#
class MDUSA_service_item(db.Model):
    __tablename__ = 'USA_service_item'
    id = db.Column(db.Integer)  # ID
    USA_service_contract_id = db.Column(db.Integer, db.ForeignKey(
        "USA_service_contract.id"), primary_key=True)  # 用户合同ID（外键）
    service_Item_id = db.Column(db.Integer, db.ForeignKey(
        "Service_Item.id"), primary_key=True)  # 服务项ID（外键）


# USA合同-组织（N-N交叉表）
#
class MDUSA_org(db.Model):
    __tablename__ = 'USA_org'
    # id = db.Column('id', db.Integer, primary_key=True)  # ID主键
    USA_service_contract_id = db.Column(db.Integer, db.ForeignKey(
        "USA_service_contract.id"), primary_key=True)  # 用户合同ID（外键）
    org_id = db.Column(db.Integer, db.ForeignKey(
        "Organization.id"), primary_key=True)  # 组织结构ID（外键）


# 用户表
#
class MDuser(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(20))  # 用户名称
    nickname = db.Column(db.String(20))  # 用户昵称
    # 联系人数据接口,如果为空则从本地数据库获取。 ——将来可能使用接口关联相关的联系人信息
    external_hrApi_id = db.Column(db.Integer, db.ForeignKey('External_HRapi.id'))
    contacts_id = db.Column(db.Integer, db.ForeignKey('Contacts.id'))  # 联系人ID
    wx_session_id = db.Column(db.String(128))  # 微信登录ID
    wx_open_id = db.Column(db.String(128))  # 微信登录ID
    create_date = db.Column(db.Integer)  # 建立日期
    last_date = db.Column(db.Integer)  # 最后登录日期
    token = db.Column(db.String(500))

    bind_status = db.Column(db.Integer)  # 绑定状态

    attachment = db.relationship('MDAttachment', backref='user', lazy='dynamic')
    service_item_agent = db.relationship('MDService_Item_agent',
                                         backref='user', lazy='dynamic')
    user_service_list = db.relationship('MDService_list',
                                   backref='user', lazy='dynamic', foreign_keys="MDService_list.user_id")
    agent_service_list = db.relationship('MDService_list',
                                   backref='agent', lazy='dynamic', foreign_keys="MDService_list.agent_id")

    task_list = db.relationship('MDService_list_taskList',
                                backref='worker', lazy='dynamic')

    service_list_evaluate = db.relationship('MDService_list_evaluate',
                                            backref='user', lazy='dynamic')

    service_list_goods = db.relationship('MDService_list_goods',
                                         backref='user', lazy='dynamic')
    allot_task = db.relationship('MDAllot_task',
                                         backref='user', lazy='dynamic')

    def __str__(self):
        return self.name


# -----------------------------------------------------HR关联----------------------------------------------------------


# 外部HR接口API表
#
class MDExternal_HRapi(db.Model):
    __tablename__ = 'External_HRapi'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(20))  # 用户名称
    secret = db.Column(db.String(50))

    user = db.relationship('MDuser', backref='external_hrapi', lazy='dynamic')
    def __str__(self):
        return self.name

# 联系人表
#
class MDContacts(db.Model):
    __tablename__ = 'Contacts'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(20))  # 姓名
    org_id = db.Column(db.Integer, db.ForeignKey('Organization.id'))  # 部门ID
    phone = db.Column(db.String(20))  # 电话
    address = db.Column(db.String(100))  # 地址
    create_date = db.Column(db.Integer)  # 建立日期
    last_date = db.Column(db.Integer)  # 信息最后更新日期
    bind_status = db.Column(db.Integer)  # 绑定状态

    user = db.relationship('MDuser', backref='contacts', lazy='dynamic')
    service_list_contact = db.relationship('MDService_list_contact', backref='contacts', lazy='dynamic')
    def __str__(self):
        return self.name


# 组织结构表
#
class MDOrganization(db.Model):
    __tablename__ = 'Organization'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    name = db.Column(db.String(20))  # 组织名称
    create_date = db.Column(db.Integer)  # 建立日期
    last_date = db.Column(db.Integer)  # 信息最后更新日期

    contacts = db.relationship('MDContacts',
                                backref='organization', lazy='dynamic')

    parent_id = db.Column(db.Integer, db.ForeignKey("Organization.id"))  # 上级组织ID (根组织=null)

    parent = db.relationship("MDOrganization", remote_side=[id],
                             backref=db.backref('childs', lazy='dynamic'))

    service_vendor = db.relationship('MDService_vendor',
                                     backref='organization', lazy='dynamic')
    def __str__(self):
        return self.name

# -----------------------------------------------------服务业务----------------------------------------------------------
# 服务单表
#
class MDService_list(db.Model):
    __tablename__ = 'Service_list'
    id = db.Column(db.Integer, primary_key=True)  # ID主键

    parent = db.relationship("MDService_list", remote_side=[id],
                             backref=db.backref('childs', lazy='dynamic'))
    parents_id = db.Column(db.Integer, db.ForeignKey("Service_list.id"))  # 父级服务单ID

    source = db.Column(db.Integer)  # 发起源参考 SERVER_SOURCE
    usa_service_item_id = db.Column(db.Integer)  # USA服务项目ID
    # usa_service_item_id = db.Column(db.Integer, db.ForeignKey(
    #     'USA_service_item.id'))  # USA服务项目ID

    title = db.Column(db.String(100))  # 标题
    descript = db.Column(db.String(250))  # 描述
    scope = db.Column(db.Integer)  # 影响范围 SCOPE
    urgency = db.Column(db.Integer)  # 紧急度 URGENCY
    tick_id = db.Column(db.Integer)  # 流程id

    service_item_id = db.Column(db.Integer, db.ForeignKey("Service_Item.id"))  # 服务项目ID（外键）

    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # 发起人ID

    agent_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # 受理人ID
    service_level_agreemnts_id = db.Column(db.Integer, db.ForeignKey(
        'Service_level_agreemnts.id'))  # 服务级别协议ID（服务台根据 影响范围和紧急度选择不同的级别）

    # 以下三个字段，数据来源于服务级别协议
    cost = db.Column(db.Numeric(10, 2))  # 服务费
    promise_tto = db.Column(db.Integer)  # 理论响应时间 (时间戳)
    promise_ttr = db.Column(db.Integer)  # 理论解决时间 (时间戳)

    price = db.Column(db.Numeric(10, 2))  # 物品总费用

    create_date = db.Column(db.Integer)  # 发起日期
    accept_date = db.Column(db.Integer)  # 受理日期
    assign_date = db.Column(db.Integer)  # 分配日期
    resolve_date = db.Column(db.Integer)  # 解决日期

    advise = db.Column(db.String(250)) # 拒绝原因

    solution_id = db.Column(db.Integer, db.ForeignKey(
        'Service_Item_solution.id'))  # 服务项解决方案ID
    closeing_statment = db.Column(db.String(250))  # 结案说明

    service_status = db.Column(db.Integer)  # 状态 参考 SERVICE_STATUS

    task_list = db.relationship('MDService_list_taskList',
                                backref='service_list', lazy='dynamic')

    contact = db.relationship('MDService_list_contact',
                              backref='service_list', lazy='dynamic')

    evaluate = db.relationship('MDService_list_evaluate',
                               backref='service_list', lazy='dynamic')

    goods = db.relationship('MDService_list_goods',
                            backref='service_list', lazy='dynamic')
    def __str__(self):
        return self.title

    def to_basic_dict(self):
        resp_dict = {
            "id": self.id,
            "title": self.title,
            "urgency": urgency_transition(self.urgency),
            "user": self.user.name,
            "time": time.strftime("%Y-%m-%d", time.localtime(self.create_date)),
            "status": service_list_status_transition(self.service_status),
            "service_item": self.service_item.name
        }
        return resp_dict

# 工作任务表
#
class MDService_list_taskList(db.Model):
    __tablename__ = 'Service_list_taskList'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    service_list_id = db.Column(db.Integer, db.ForeignKey("Service_list.id"))  # 服务单ID（外键）
    name = db.Column(db.String(100))  # 任务名称
    descript = db.Column(db.String(250))  # 描述

    worker_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # 工作者ID

    create_date = db.Column(db.Integer)  # 建立日期
    response_date = db.Column(db.Integer)  # 响应日期
    close_date = db.Column(db.Integer)  # 关闭日期

    closeing_statment = db.Column(db.String(250))  # 结案说明

    status = db.Column(db.Integer)  # 状态 参考 TASK_STATUS

    pause_date = db.Column(db.Integer)  # 暂停日期
    pause_time = db.Column(db.Integer)  # 暂停时间，秒

    def to_basic_dict(self):
        resp_dict = {
            "id": self.id,
            "title": self.service_list.title,
            "urgency": urgency_transition(self.service_list.urgency),
            "user": self.service_list.user.name,
            "time": time.strftime("%Y-%m-%d", time.localtime(self.service_list.create_date)),
            "status": service_list_status_transition(self.service_list.service_status),
            "task_status": service_list_task_status_transition(self.status),
            "service_item": self.service_list.service_item.name
        }
        return resp_dict

    def __str__(self):
        return self.name
# 任务附件
#
class MDTask_attachment(db.Model):
    __tablename__ = 'Task_attachment'
    # id = db.Column('id', db.Integer, primary_key=True)  # ID主键

    taskList_id = db.Column(db.Integer, db.ForeignKey(
        "Service_list_taskList.id"), primary_key=True)  # 任务单ID（外键）
    attachment_id = db.Column(db.Integer, db.ForeignKey(
        "Attachment.id"), primary_key=True)  # 附件ID（外键）


# 服务单联系人（考虑到会有组织外人员参与，此处未和系统的组织架构联系作关联）
#
class MDService_list_contact(db.Model):
    __tablename__ = 'Service_list_contact'
    id = db.Column(db.Integer, primary_key=True)  # ID主键
    service_list_id = db.Column(db.Integer, db.ForeignKey(
        "Service_list.id"))  # 服务单ID（外键）
    contact_id = db.Column(db.Integer, db.ForeignKey(
        "Contacts.id"))  # 联系人ID（外键）
    name = db.Column(db.String(50))  # 联系人姓名
    phone = db.Column(db.String(20))  # 联系电话
    memo = db.Column(db.String(100))  # 工作分担
    create_date = db.Column(db.Integer)  # 分担日期
    def __str__(self):
        return self.name

# 服务单附件
#
class MDService_list_attachment(db.Model):
    __tablename__ = 'Service_list_attachment'
    # id = db.Column('id', db.Integer, primary_key=True)  # ID主键

    service_list_id = db.Column(db.Integer, db.ForeignKey(
        "Service_list.id"), primary_key=True)  # 服务单ID（外键）
    attachment_id = db.Column(db.Integer, db.ForeignKey(
        "Attachment.id"), primary_key=True)  # 附件ID（外键）


# 服务单评价
#
class MDService_list_evaluate(db.Model):
    __tablename__ = 'Service_list_evaluate'
    id = db.Column(db.Integer, primary_key=True)  # ID主键

    service_list_id = db.Column(db.Integer, db.ForeignKey(
        "Service_list.id"))  # 服务单ID（外键）
    service_Item_evaluate_id = db.Column(db.Integer, db.ForeignKey(
        "Service_Item_evaluate.id"))  # 评价表ID（外键）
    score = db.Column(db.Float)  # 得分

    create_date = db.Column(db.Integer)  # 评价日期
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # 评价人ID


# 服务单物品表
#
class MDService_list_goods(db.Model):
    __tablename__ = 'Service_list_goods'
    id = db.Column(db.Integer, primary_key=True)  # ID主键

    service_list_id = db.Column(db.Integer, db.ForeignKey(
        "Service_list.id"))  # 服务单ID（外键）
    goods_id = db.Column(db.Integer, db.ForeignKey("Goods.id"))  # 物品id
    qty = db.Column(db.Integer, default=0)  # 物品数量
    create_date = db.Column(db.Integer)  # 分配日期
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # 使用人id
    goods_cost = db.Column(db.Numeric(10, 2))  # 物品总费用


# 定时任务创建工单表
#
class MDTiming_task(db.Model):
    __tablename__ = 'timing_task'
    id = db.Column(db.Integer, primary_key=True)  # ID主键

    task_name = db.Column(db.String(255)) # 工单名称

    service_item_id = db.Column(db.Integer, db.ForeignKey(
        "Service_Item.id"))  # 服务项目ID（外键）
    urgency = db.Column(db.Integer)  # 紧急度
    scope = db.Column(db.Integer)  # 影响范围
    period = db.Column(db.Integer)  # 周期
    descript = db.Column(db.String(255))  # 描述
    task_time = db.Column(db.DateTime) # 时间
    cost = db.Column(db.Numeric(10, 2))  # 服务费

    allot_task = db.relationship('MDAllot_task',
                            backref='timing_task', lazy='dynamic')

    def __str__(self):
        return self.task_name


# 定时任务创建工单默认执行人表
#
class MDAllot_task(db.Model):
    __tablename__ = 'allot_task'
    id = db.Column(db.Integer, primary_key=True)  # ID主键

    plan_task_name = db.Column(db.String(255)) # 任务名称
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))  # 执行人id
    timing_task_id = db.Column(db.Integer, db.ForeignKey(
        "timing_task.id"))  # 定时任务创建工单表ID（外键）
    descript = db.Column(db.String(255))  # 描述
    def __str__(self):
        return self.plan_task_name

admin.add_view(BaseView(MDTiming_task, db.session, name="定时创建工单", category='定时填单'))
admin.add_view(BaseView(MDAllot_task, db.session, name="默认执行人", category='定时填单'))



class SuperUser(db.Model):
    __tablename__ = 'super_user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    # login = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(64))

    def __str__(self):
        return self.name
    @property
    def password(self):
        raise AttributeError("当前属性不可读")

    @password.setter
    def password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_poassword(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login integration
    # NOTE: is_authenticated, is_active, and is_anonymous
    # are methods in Flask-Login < 0.3.0
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username

# # Create customized model view class
# class MyModelView(ModelView):
#
#     def is_accessible(self):
#         return login.current_user.is_authenticated
#
#     def inaccessible_callback(self, name, **kwargs):
#         # redirect to login page if user doesn't have access
#
#         return redirect(url_for('admin.login_view', next=request.url))
# # Add view
# admin.add_view(MyModelView(SuperUser, db.session))



class MDAttachmentView(ModelView):
    column_labels = dict(name='名称')
    column_exclude_list = ['data', ]
    column_searchable_list = ['name', 'length']
    column_filters = ['use_num']
    column_editable_list = ['name', ]
    form_ajax_refs = {
        'user': {
            'fields': ['name'],
            'page_size': 10
        }
    }
# admin.add_sub_category(name="Links", parent_name="Team")
# admin.add_link(MenuLink(name='Home Page', url='/', category='Links'))

admin.add_view(MdService_ClusterView(MdService_Cluster, db.session, name="服务簇", category='服务'))
admin.add_view(MDServiceView(MDService, db.session, name="服务", category='服务'))
admin.add_view(BaseView(MDService_Type, db.session, name="服务项目类型", category='服务'))
admin.add_view(BaseView(MDService_Item, db.session, name="服务项目", category='服务'))
admin.add_view(BaseView(MDService_Item_agent, db.session, name="服务项目代理人", category='服务'))
admin.add_view(BaseView(MDService_Item_evaluate, db.session, name="服务项目评价分类", category='服务'))
admin.add_view(BaseView(MDService_Item_solution, db.session, name="服务项目解决方案", category='服务'))
admin.add_view(BaseView(MDService_level_agreements, db.session, name="服务级别协议", category='服务'))
admin.add_view(BaseView(MDService_level_params, db.session, name="服务参数", category='服务'))
admin.add_view(BaseView(MDService_vendor, db.session, name="服务供应商", category='服务'))
admin.add_view(BaseView(MDService_contract, db.session, name="服务合同", category='服务'))
admin.add_view(BaseView(MDUSA_service_contract, db.session, name="用户服务合同", category='服务'))

admin.add_view(MDAttachmentView(MDAttachment, db.session, name="附件"))

admin.add_view(BaseView(MDGoods, db.session, name="物品"))

admin.add_view(BaseView(MDuser, db.session, name="用户", category='人员'))
admin.add_view(BaseView(MDContacts, db.session, name="联系人", category='人员'))
admin.add_view(BaseView(MDOrganization, db.session, name="组织结构", category='人员'))
admin.add_view(BaseView(MDExternal_HRapi, db.session, name="外部HR接口", category='人员'))


admin.add_view(BaseView(MDService_list, db.session, name="服务单", category='服务单'))
admin.add_view(BaseView(MDService_list_taskList, db.session, name="工作任务", category='服务单'))
admin.add_view(BaseView(MDService_list_contact, db.session, name="服务单联系人", category='服务单'))
admin.add_view(BaseView(MDService_list_evaluate, db.session, name="服务单评价", category='服务单'))
admin.add_view(BaseView(MDService_list_goods, db.session, name="服务单商品", category='服务单'))
