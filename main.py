# -*- encoding: utf-8 -*-

import sys
import requests

from apscheduler.schedulers.blocking import BlockingScheduler
from utils.log import logger
from ths_trader import THSTrader
from config import ths_xiadan_path, SCKey


def is_test():
    if len(sys.argv) > 1 and sys.argv[1] != 'test':
        return False
    return True


def buy_convert_bond():
    """
    申购可转债
    """
    push_message = ''

    try:
        ths_trader = THSTrader(ths_xiadan_path)
        res = ths_trader.auto_ipo()
        push_message += str(res) + '\n'
    except Exception as e:
        logger.error("auto_ipo failed, err: %s" % e)
        push_message += str(e)
    finally:
        if not is_test():
            push_url = 'http://sc.ftqq.com/' + SCKey + '.send'
            data = {'text': '今日新股新债申购通知', 'desp': push_message}
            resp = requests.post(push_url, data=data).json()
            logger.info("requests, resp: %s" % resp)
        else:
            logger.info(push_message)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'cron':
        scheduler = BlockingScheduler(timezone="Asia/Shanghai")
        scheduler.add_job(buy_convert_bond, 'cron', day_of_week='0-4', hour=9, minute=40)
        scheduler.start()
    if is_test():
        buy_convert_bond()
