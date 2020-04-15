



def urgency_transition(urgency_id):

    if urgency_id == 1:
        return "低"
    elif urgency_id == 2:
        return "中"
    elif urgency_id == 3:
        return "高"
    else:
        return "非常高"

def scope_transition(scope_id):

    if scope_id == 1:
        return "个人"
    elif scope_id == 2:
        return "部门"
    else:
        return "公司"




def service_list_status_transition(status):

    if status == 1:
        return "待审批"
    elif status == 2:
        return "待分配"
    elif status == 3:
        return "待响应"
    elif status == 4:
        return "执行中"
    elif status == 5:
        return "暂停中"
    elif status == 6:
        return "待结案"
    elif status == 7:
        return "待评分"
    else:
        return "已完成"

def service_list_status_title_transition(status):

    if status == 2:
        return "分配"
    elif status == 3:
        return "执行"
    elif status == 4:
        return "执行"
    elif status == 6:
        return "结案"
    elif status == 7:
        return "评分"
    elif status == 8:
        return "完成"




def service_list_task_status_transition(status):

    if status == 1:
        return "已放弃"
    elif status == 2:
        return "待响应"
    elif status == 3:
        return "执行中"
    elif status == 4:
        return "暂停中"
    elif status == 6:
        return "已驳回"
    else:
        return "已完成"