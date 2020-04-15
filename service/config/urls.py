# 新建工单
NEW_TICKET = 'api/v1.0/tickets'


# 查询工单流程
TICKET_STEPS = 'api/v1.0/tickets/{}/flowsteps'


# 查询我的审批
MY_APPROVE = 'api/v1.0/tickets?category={}'

# 处理工单
DISPOSE_TICKET = 'api/v1.0/tickets/{}'

# 获取工单操作
GET_TICKET_OPERATION = 'api/v1.0/tickets/{}/transitions'

# 获取新建工单操作
GET_NEW_TICKST_OPERATION = 'api/v1.0/workflows/{}/init_state'

#　审批
APPROVE_SERVICE_LIST = 'api/v1.0/tickets/{}'

# 获取状态
GET_SERVICE_LIAT_STATUS = 'api/v1.0/tickets/{}/participant_info'