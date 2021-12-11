# -*- encoding: utf-8 -*-
"""
爬取来自东方财富网的最新可转债信息：http://data.eastmoney.com/kzz/default.html
接口示例：http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get?type=KZZ_LB2.0&token=70f12f2f4f091e459a279469fe49eca5&cmd=&st=STARTDATE&sr=-1&p=1&ps=6
"""

import requests
import time
from config import headers
from utils.log import logger


class EastSpider():
    def __init__(self):
        super(EastSpider, self).__init__()
        self.url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'

    def get_bond_list(self):
        """
        从东方财富获取可转债数据
        """
        params = {
            'sortColumns': 'PUBLIC_START_DATE',
            'sortTypes': '-1',
            'pageSize': '10',
            'pageNumber': '1',
            'reportName': 'RPT_BOND_CB_LIST',
            'columns': 'ALL',
            'source': 'WEB',
            'client': 'WEB'
        }
        ret_dict = requests.get(self.url, params=params, headers=headers).json()
        data = ret_dict['result']['data']
        return data

    def get_date_bond_list(self, date):
        """
        获取指定日期的可转债id列表
        :param date: %Y-%m-%d 格式的日期
        """
        try:
            data = self.get_bond_list()
        except Exception as e:  # API偶尔解析错误，直接返回空list
            logger.info("get bond list failed, err: %s" % e)
            data = []

        ret = []
        for stock in data:
            if stock['VALUE_DATE'].split()[0] == date:
                ret.append(stock['CORRECODE'])

        logger.info("today is: %s, bond_list: %s" % (date, ret))
        return ret

    def get_today_bond_list(self) -> list:
        """
        获取当日可转债列表
        """
        today_str = time.strftime("%Y-%m-%d", time.localtime())
        return self.get_date_bond_list(today_str)

    def get_stock_list(self):
        """
        获取按申购日期排序的前50股票
        """
        params = {
            'sortColumns': 'APPLY_DATE',
            'sortTypes': '-1',
            'pageSize': '50',
            'pageNumber': '1',
            'reportName': 'RPTA_APP_IPOAPPLY',
            'columns': 'ALL',
            'source': 'WEB',
            'client': 'WEB'
        }
        ret_dict = requests.get(self.url, params=params, headers=headers).json()
        return ret_dict['result']['data']

    def get_date_stock_list(self, date):
        """
        获取指定日期的股票列表
        """
        try:
            data = self.get_stock_list()
        except Exception as e:
            logger.info("get stock list failed, err: %s" % e)
            data = []

        ret = []
        for stock in data:
            if stock['APPLY_DATE'].split()[0] == date:
                ret.append({"id": stock['APPLY_CODE'],"name": stock['SECURITY_NAME'], 'price': stock['ISSUE_PRICE']})

        logger.info("today is: %s, stock_list: %s" % (date, ret))
        return ret

    def get_today_stock(self):
        """
        获取当天的股票列表
        """
        today_str = time.strftime("%Y-%m-%d", time.localtime())
        return self.get_date_stock_list(today_str)


if __name__ == '__main__':
    spider = EastSpider()
    # print(spider.get_today_bond_list())
    print(spider.get_today_stock())
