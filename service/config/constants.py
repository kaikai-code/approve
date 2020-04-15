


# token过期时间
TOKEN_EXPIRATION_TIME = 604800

# 短信验证码Redis有效期，单位：秒
SMS_CODE_REDIS_EXPIRES = 300

# 服务单id列表的过期时间
SERVICE_LIST_TICK_ID_REDIS_EXPIRES = 120

# 紧急程度 * 影响范围的最大值
AGGREMMENT_PARAM = 12

# 每页的默认返回数量
# PER_PAGE = 3
PER_PAGE = 5

SERVICE_STATUS = {
    "approve": 1,
    "allot": 2,
    "answer": 3,
    "run": 4,
    "pause": 5,
    "closeing": 6,
    "grade": 7,
    "end": 8
}

SERVICE_STATUS_LIST = [1, 2, 3, 4, 5, 6, 7, 8]

TASK_STATUS = {
    "cancel": 1,
    "answer": 2,
    "run": 3,
    "pause": 4,
    "end": 5,
    "reject": 6
}

# REMIND_CRON = {
#     "day_of_week": "*",
#     "year": "*",
#     "month": "*",
#     "day": "*",
#     "hour": "8",
#     "minute": "0",
#     "second": "0",
# }

REMIND_CRON = {
    "day_of_week": "*",
    "year": "*",
    "month": "*",
    "day": "*",
    "hour": "10",
    "minute": "05",
    "second": "*/20",
}

# SUBMIT_CRON = {
#     "day_of_week": "*",
#     "year": "*",
#     "month": "*",
#     "day": "*",
#     "hour": "8",
#     "minute": "0",
#     "second": "0",
# }

SUBMIT_CRON = {
    "day_of_week": "*",
    "year": "*",
    "month": "*",
    "day": "",
    "hour": "",
    "minute": "",
    "second": "",
}

CCP_APPROVE_NUMBER = 581646

CCP_SMS_CODE_NUMBER = 581643

CCP_GIVE_UP_TASK_NUMBER = 581648

REQUEST_RETRY_COUNT = 3

SYSTEM_USER_ID = 1