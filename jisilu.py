# -*- coding:utf-8 -*-

import time
import requests
import config

class Jisilu(object):

    def __init__(self):
        self.max_line = 30
        self.session = requests.session()
        self.session.headers = {
            "Host": "www.jisilu.cn",
            "Init": "1",
            "Referer": "https://www.jisilu.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"}
        self.cookies = config.jisilu_cookie
        self.set_cookies()

    def set_cookies(self):
        """
        从字符串中提取字典形式的 cookie
        :return: dict
        """
        cookies = self.cookies.replace("Cookie: ", "").split('; ')
        cookies = {k: v for k, v in [cookie.split('=', 1) for cookie in cookies]}
        for k, v in cookies.items():
            self.session.cookies.set(k, v)

    def get_convert_bonds_data(self):
        """
        获取可转载数据
        :return:
        """
        url = "https://www.jisilu.cn/webapi/cb/list_new/"
        datas = self.session.get(url).json()
        datas = sorted(datas["data"], key=lambda x: x["dblow"])
        if len(datas) < 50:
            print("未登录")

        cnt = 0
        res = []
        for data in datas:
            # 排除未上市
            if data.get('price_tips') == '待上市':
                continue

            # 存在强赎日期
            if data['redeem_dt']:
                continue

            # 转债价格>150,跳过
            if data['price'] > 150:
                continue

            cnt += 1
            res.append(data)
            if cnt >= self.max_line:
                break

        return res

    def print_convert_bonds_data(self):
        """
        打印可转债数据
        :param bonds:
        :return:
        """
        bonds = self.get_convert_bonds_data()

        for bond in bonds:
            bond_id = bond["bond_id"]
            bond_nm = bond["bond_nm"]
            stock_id = bond["stock_id"]
            stock_nm = bond["stock_nm"]
            convert_price = bond["convert_price"]
            price = bond["price"]
            stock_price = bond["sprice"]
            convert_value = bond["convert_value"]
            premium_rt = bond["premium_rt"]
            print()
            print("债券代码: %s" % bond_id)
            print("债券名: %s" % bond_nm)
            print("股票代码: %s" % stock_id)
            print("股票名: %s" % stock_nm)
            print("转债价格: %s" % price)
            print("正股价格: %s" % stock_price)
            print("转股价: %s" % convert_price)
            print("转股价值: %s" % convert_value)
            print("溢价率: %s " % premium_rt)
            print("强赎日期: %s" % bond['redeem_dt'])


    def get_closed_fund_data(self):
        """
        获取封基列表
        :return:
        """
        timestrip = int(time.time() * 1000)
        url = "https://www.jisilu.cn/data/cf/cf_list/?___jsl=LST___t=%s" % timestrip
        data = self.session.get(url)

        data = data.json()
        ret = []
        for item in data['rows']:
            ret.append(item['cell'])

        return ret

    def format_closed_fund(self, item):
        """
        格式化输出封基信息
        :return:
        """
        col_en = ['fund_id', 'fund_nm', 'discount_rt', 'left_year', 'maturity_dt', 'discount_factor']
        col_cn = ['代码', '名称', '折价率', '剩余年限', '到期时间', '折价因子']
        res = []

        for i in range(len(col_en)):
            res.append("%s: %s" % (col_cn[i], item[col_en[i]]))

        return ', '.join(res)

    def filter_closed_fund(self, topk = 0):
        """
        筛选封闭基金
        筛选出 (折价率 - 1.5) / 剩余年限 的前十封基
        :return:
        """
        data = self.get_closed_fund_data()
        funds = []
        for item in data:
            try:
                discount_rt = float(item['discount_rt'])
                left_year = float(item['left_year'])
                funds.append({
                    'fund_id': item['fund_id'],
                    'fund_nm': item['fund_nm'],
                    'discount_rt': discount_rt,
                    'left_year': left_year,
                    'maturity_dt': item['maturity_dt'],
                    'discount_factor': (discount_rt - 1.5) / left_year
                })
            except ValueError:
                pass

        funds.sort(key=lambda x: x['discount_factor'], reverse=True)
        res = []

        if topk > 0:
            funds = funds[:topk]

        for item in funds:
            res.append(item)
            print(self.format_closed_fund(item))

        return res


if __name__ == '__main__':
    jsl = Jisilu()
    print(jsl.filter_closed_fund(10))
