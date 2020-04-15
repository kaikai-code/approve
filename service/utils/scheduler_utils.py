

from apscheduler.schedulers.blocking import BlockingScheduler
import datetime
from ..config.config import Config

class SchedulerTask(object):

    def __init__(self):
        self.__sched = BlockingScheduler()

    def add_job(self, func, args=(), **cron):

        self.__sched.add_job(func, "cron", args, **cron, coalesce=True,
                             misfire_grace_time=Config.MISFIRE_GRACE_TIME,
                             max_instances=Config.MAX_INSTANCES)

    def start(self):
        self.__sched.start()

    def shutdown(self, wait=True):           
        self.__sched.shutdown(wait)
        self.__sched = None


scheduler_task = SchedulerTask()