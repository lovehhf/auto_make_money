# -*- encoding: utf-8 -*-

import sys
import requests

from apscheduler.schedulers.blocking import BlockingScheduler
from utils import logger
from ths_trader import THSTrader
from spider import EastSpider
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
        spider = EastSpider()
        today_bond_list = spider.get_today_bond_list()

        if not today_bond_list:
            raise Exception("今日没有可申购的可转债")

        ths_trader = THSTrader(ths_xiadan_path)
        res = ths_trader.buy_bonds(today_bond_list)
        push_message += str(res) + '\n'
    except Exception as e:
        push_message += str(e)
    finally:
        if not is_test():
            push_url = 'http://sc.ftqq.com/' + SCKey + '.send'
            resp = requests.get(push_url, params={'text': '今日可转债通知', 'desp': push_message}).json
            logger.info("requests, resp: %s" % resp)
        else:
            logger.info(push_message)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'cron':
        scheduler = BlockingScheduler(timezone="Asia/Shanghai")
        scheduler.add_job(buy_convert_bond, 'cron', day_of_week='1-5', hour=9, minute=40)
        scheduler.start()
    if is_test():
        buy_convert_bond()
