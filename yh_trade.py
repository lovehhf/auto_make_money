# coding:utf-8

from ths_trader import THSTrader
from jisilu import Jisilu

"""
银河证券交易客户端
"""


class YHTrader(THSTrader):

    def __init__(self, exe_path):
        super().__init__(exe_path)
        self.jsl = Jisilu()

    def get_closed_funds(self):
        """
        获取封闭基金列表
        """
        data = self.jsl.get_closed_fund_data()
        return data

    def format_closed_fund(self, item):
        """
        格式化输出封基信息
        :return:
        """
        col_en = ['fund_id', 'fund_nm', 'discount_rt', 'left_year', 'maturity_dt', 'discount_factor', 'rank']
        col_cn = ['代码', '名称', '折价率', '剩余年限', '到期时间', '折价因子', '排名']
        res = []

        for i in range(len(col_en)):
            res.append("%s: %s" % (col_cn[i], item[col_en[i]]))

        return ', '.join(res)

    def compare_closed_fund_position(self):
        """
        比较持仓数据
        """
        data = self.get_closed_funds()
        funds = {}
        for item in data:
            try:
                discount_rt = float(item['discount_rt'])
                left_year = float(item['left_year'])

                funds[item['fund_id']] = {
                    'fund_id': item['fund_id'],
                    'fund_nm': item['fund_nm'],
                    'discount_rt': discount_rt,
                    'left_year': left_year,
                    'maturity_dt': item['maturity_dt'],
                    'discount_factor': (discount_rt - 1.5) / left_year
                }
            except ValueError:
                pass

        funds_arr = sorted(funds.values(), key=lambda x: x['discount_factor'], reverse=True)
        for i in range(len(funds_arr)):
            id = funds_arr[i]['fund_id']
            funds[id]['rank'] = i

        positions = self.get_position()
        for position in positions:
            id = position['证券代码']

            if not id in funds:
                continue

            name = position['证券名称']
            amount = position['股份余额']
            price = position['参考市价']
            money = position['参考市值']

            item = funds[id]
            print(self.format_closed_fund(item))


if __name__ == '__main__':
    exe_path = "C:\\双子星-中国银河证券\\xiadan.exe"
    yhclient = YHTrader(exe_path)

    # data = yhclient.get_position()
    # import json
    # print(json.dumps(data, indent=4, ensure_ascii=False))

    yhclient.compare_closed_fund_position()