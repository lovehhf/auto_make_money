# -*- encoding: utf-8 -*-

import sys
import requests

from apscheduler.schedulers.blocking import BlockingScheduler
from utils import logger
from ths_trader import THSTrader
from spider import EastSpider
from config import ths_xiadan_path, SCKey

is_test = True

def buy_convert_bond():
    """
    申购可转债
    """
    push_message = ''

    try:
        ths_trader = THSTrader(ths_xiadan_path)
        spider = EastSpider()
        today_bond_list = spider.get_today_list()
        if not today_bond_list:
            raise Exception("今日没有可申购的可转债")

        res = ths_trader.buy_bonds(today_bond_list)
        push_message += str(res) + '\n'

    except Exception as e:
        push_message += str(e)
    finally:
        if not is_test:
            resp = requests.get('http://sc.ftqq.com/' + SCKey + '.send', params={'text': '今日可转债通知', 'desp': push_message})
            logger.info("requests, resp: %s" % resp.text)

        print(push_message)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'cron':
        scheduler = BlockingScheduler()
        scheduler.add_job(buy_convert_bond, 'cron', day_of_week='1-5', hour=9, minute=35)
        scheduler.start()
        is_test = False

    if is_test:
        buy_convert_bond()
