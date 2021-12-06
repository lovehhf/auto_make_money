# -*- encoding: utf-8 -*-
"""
爬取来自东方财富网的最新可转债信息：http://data.eastmoney.com/kzz/default.html
接口示例：http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get?type=KZZ_LB2.0&token=70f12f2f4f091e459a279469fe49eca5&cmd=&st=STARTDATE&sr=-1&p=1&ps=6
"""
import re

from config import headers
import abc
import requests
import json
import time


class BaseSpider(abc.ABC):
    def __init__(self, url=None):
        pass

    def _get_token(self) -> str:
        pass

    def get_today_list(self) -> list:
        pass


class EastSpider(BaseSpider):
    # 新东方财富网API移除了token验证字段，感谢！
    def __init__(self, url='https://datacenter-web.eastmoney.com/api/data/v1/get'):
        super(EastSpider, self).__init__()
        self.url = url
        self.params = {
            'sortColumns': 'PUBLIC_START_DATE',
            'sortTypes': '-1',
            'pageSize': '10',
            'pageNumber': '1',
            'reportName': 'RPT_BOND_CB_LIST',
            'columns': 'ALL',
            'source': 'WEB',
            'client': 'WEB'
        }

    def get_list(self):
        r = requests.get(self.url, params=self.params, headers=headers)
        ret_dict = json.loads(r.text)
        try:
            data: list = ret_dict['result']['data']
            return data
        except KeyError:
            raise RuntimeError('API解析错误')

    def get_today_list(self) -> list:
        try:
            r_list = self.get_list()
        except RuntimeError as e:  # API偶尔解析错误，直接返回空list
            print(str(e))
            return []

        today_str = time.strftime("%Y-%m-%d", time.localtime())
        today_str = '2021-12-08'
        today_list = []
        for stock in r_list:
            if stock['VALUE_DATE'].split()[0] == today_str:
                today_list.append(stock['CORRECODE'])

        print("today is: %s, todat_list: %s" % (today_str, today_list))
        return today_list


if __name__ == '__main__':
    spider = EastSpider()
    print(spider.get_today_list())
