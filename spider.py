# -*- encoding: utf-8 -*-
"""
爬取来自东方财富网的最新可转债信息：http://data.eastmoney.com/kzz/default.html
接口示例：http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get?type=KZZ_LB2.0&token=70f12f2f4f091e459a279469fe49eca5&cmd=&st=STARTDATE&sr=-1&p=1&ps=6
"""

import abc
import requests
import time
from config import headers
from utils import logger


class EastSpider():
    def __init__(self):
        super(EastSpider, self).__init__()
        self.url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'

    def get_bond_list(self):
        """
        从东方财富获取可转债数据
        """
        try:
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
        except Exception as e:
            raise RuntimeError('get list from eastmoney failed, err: %s' % e)

    def get_date_bond_list(self, date):
        """
        获取指定日期的可转债id列表
        :param date: %Y-%m-%d 格式的日期
        """
        try:
            data = self.get_bond_list()
        except RuntimeError as e:  # API偶尔解析错误，直接返回空list
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


if __name__ == '__main__':
    spider = EastSpider()
    print(spider.get_today_bond_list())
