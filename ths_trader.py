# -*- encoding: utf-8 -*-
"""
同花顺通用wrapper 来自easytrader
link： https://github.com/shidenggui/easytrader
"""

import time
import functools
import tempfile
import pandas as pd
import pywinauto
from pywinauto import win32defines, findwindows, timings
from pywinauto.win32functions import SetForegroundWindow, ShowWindow

import config
from utils.log import logger
from spider import EastSpider


def get_code_type(code):
    """
    判断代码是属于那种类型，目前仅支持 ['fund', 'stock']
    :return str 返回code类型, fund 基金 stock 股票
    """
    if code.startswith(('00', '30', '60')):
        return 'stock'
    return 'fund'


def round_price_by_code(price, code):
    """
    根据代码类型[股票，基金] 截取制定位数的价格
    :param price: 证券价格
    :param code: 证券代码
    :return: str 截断后的价格的字符串表示
    """
    if isinstance(price, str):
        return price

    typ = get_code_type(code)
    if typ == 'fund':
        return '{:.3f}'.format(price)
    return '{:.2f}'.format(price)


def set_foreground(window):
    if window.has_style(win32defines.WS_MINIMIZE):  # if minimized
        ShowWindow(window.wrapper_object(), 9)  # restore window state
    else:
        SetForegroundWindow(window.wrapper_object())  # bring to front


class THSTrader():
    def __init__(self, exe_path):
        super().__init__()
        self.connect(exe_path)
        self.spider = EastSpider()

    def connect(self, exe_path: str):
        try:
            self._app = pywinauto.Application().connect(path=exe_path, timeout=3)
        except Exception as e:
            logger.warning("try connect exe_path: %s failed, err: %s, try start it" % (exe_path, e))
            self._app = pywinauto.Application().start(exe_path)

        self._close_prompt_windows()
        self._main = self._app.top_window()
        self._init_toolbar()

    def _close_prompt_windows(self):
        """
        关闭提示窗口
        """
        self.wait(1)
        for window in self._app.windows(class_name="#32770", visible_only=True):
            title = window.window_text()
            if title != config.TITLE:
                logger.info("close " + title)
                window.close()
                self.wait(0.2)
        self.wait(1)

    def wait(self, seconds):
        time.sleep(seconds)

    def _init_toolbar(self):
        """
        初始化工具栏
        ToolbarWindow32 退出，登录，锁屏等操作所在工具栏的类名
        """
        self._toolbar = self._main.child_window(class_name="ToolbarWindow32")

    def get_account_name(self):
        """
        获取账户名
        """
        ret = ""

        try:
            dialog = self._toolbar.child_window(control_id=0x912, class_name="ComboBox")
            ret = dialog.window_text()
        except Exception as e:
            logger.error("get_account_name failed, err: %s" % e)

        return ret

    def auto_ipo(self):
        """
        自动申购可转债和新股
        """
        ret = ""
        for i in range(1, config.ACCOUNT_COUNT + 1):
            set_foreground(self._main)
            self.wait(1)

            if config.ACCOUNT_COUNT > 1:
                key = '%%%s' % i
                self.wait(3)
                pywinauto.keyboard.send_keys(key)
                name = self.get_account_name()
                logger.info("press alt + %s to switch account to: %s" % (i, name))
                ret += name + "\n"

            logger.info("start apply bonds")
            ret += self.apple_bonds() + "\n"
            self.wait(1)

            logger.info("start apply stocks")
            ret += self.apply_stocks() + "\n"
            self.wait(1)

            ret += '=' * 20 + "\n"

        return ret

    def apple_bonds(self):
        """
        申购可转债
        """
        price, amount = 100, 10000
        bonds = self.spider.get_today_bond_list()

        if not bonds:
            return "今日无可转债可申购"

        ret = ""
        for bond_id in bonds:
            try:
                self.buy(bond_id, price, amount)
                ret += "可转债: %s 申购成功;" % bond_id
                self.wait(1)
            except Exception as e:
                logger.error("buy bond: %s failed, err: %s" % bond_id, e)
                ret += "可转债: %s 申购失败;\n" % bond_id

        return ret

    def buy(self, security, price, amount, **kwargs):
        self._switch_left_menus(["买入[F1]"])
        return self.trade(security, price, amount)

    def _switch_left_menus(self, path, sleep=0.2):
        """
        点击左侧菜单栏里面指定的按钮
        """
        self._get_left_menus_handle().get_item(path).click()
        self.wait(sleep)

    @functools.lru_cache()
    def _get_left_menus_handle(self):
        """
        获取左侧的菜单栏dialog
        """
        count = 2
        while True:
            try:
                # self._main.set_focus()
                handle = self._main.child_window(
                    control_id=0x81, class_name="SysTreeView32"
                )

                if count <= 0:
                    return handle

                # sometime can't find handle ready, must retry
                handle.wait("ready", 2)
                return handle
            # pylint: disable=broad-except
            except Exception as e:
                logger.exception("error occurred when trying to get left menus, err: %s" % e)
            count = count - 1

    def trade(self, security, price, amount):
        """
        :param security: 股票id
        :param price: 价格
        :param amount: 数量
        """
        self._set_trade_params(security, price, amount)
        self._submit_trade()
        self._handle_pop_dialogs()

    def _handle_pop_dialogs(self):
        """
        处理弹出的窗口
        """
        cnt = 0
        while self.is_exist_pop_dialog():
            pywinauto.keyboard.send_keys('{ENTER}')
            logger.info("exist_pop_dialog, press enter.")
            self.wait(1)
            cnt += 1
            if cnt >= 3:
                self._main.set_focus()
                break

    def _set_trade_params(self, code, price, amount):
        """
        设置交易参数
        """
        logger.info("set_trade_params，code: %s, price: %s, amount: %s" % (code, price, amount))
        self._type_edit_control_keys(config.TRADE_SECURITY_CONTROL_ID, code)

        # wait security input finish
        self.wait(0.5)

        self._type_edit_control_keys(
            config.TRADE_PRICE_CONTROL_ID,
            round_price_by_code(price, code),
        )

        self.wait(0.5)
        self._type_edit_control_keys(
            config.TRADE_AMOUNT_CONTROL_ID, str(int(amount))
        )

    def _type_edit_control_keys(self, control_id, text):
        """
        在指定的控件输入文本
        """
        logger.info("type_edit_control_keys, control_id: %s, text: %s" % (control_id, text))
        editor = self._main.child_window(control_id=control_id, class_name="Edit")
        editor.select()
        # pywinauto.keyboard.send_keys('^a')
        # pywinauto.keyboard.send_keys('{DEL}')
        editor.type_keys(text)

    def _submit_trade(self):
        time.sleep(0.2)
        self._main.child_window(
            control_id=config.TRADE_SUBMIT_CONTROL_ID, class_name="Button"
        ).click()

    def is_exist_pop_dialog(self):
        self.wait(0.5)  # wait dialog display
        try:
            main_wrapper = self._main.wrapper_object()
            top_window_wrapper = self._app.top_window().wrapper_object()
            ret = main_wrapper != top_window_wrapper
            return ret

        except (
                findwindows.ElementNotFoundError,
                timings.TimeoutError,
                RuntimeError,
        ) as e:
            logger.exception("check pop dialog timeout, err: %s" % e)
            return False

    def _get_grid(self, control_id: int):
        grid = self._main.child_window(
            control_id=control_id, class_name="CVirtualGridCtrl"
        )
        return grid

    def _format_grid_data(self, filepath: str):
        df = pd.read_csv(
            filepath,
            delimiter="\t",
            dtype=config.GRID_DTYPE,
            na_filter=False,
            encoding="gbk"
        )
        return df.to_dict("records")

    def _get_grid_data(self, control_id):
        """
        获取通过保存到xls获取表格数据
        暂时没有用到此函数，现采用的是爬取东方财富的数据
        """
        grid = self._get_grid(control_id)
        set_foreground(grid)  # setFocus buggy, instead of SetForegroundWindow
        grid.type_keys("^s", set_foreground=False)
        count = 10
        while count > 0:
            if self.is_exist_pop_dialog():
                if self._app.top_window().window(class_name="Static", title_re=".*输入验证码.*"):
                    file_path = "tmp.png"
                    self._app.top_window().window(
                        class_name="Static", control_id=0x965
                    ).capture_as_image().save(file_path)
                    set_foreground(grid)

                    from utils.captcha import captcha_recognize
                    captcha_num = captcha_recognize("tmp.png").strip()  # 识别验证码
                    captcha_num = "".join(captcha_num.split())
                    logger.info("captcha result-->" + captcha_num)
                    if len(captcha_num) == 4:
                        editor = self._app.top_window().child_window(control_id=0x964, class_name="Edit")
                        editor.select()
                        editor.type_keys(captcha_num)
                        self._app.top_window().set_focus()
                        pywinauto.keyboard.send_keys("{ENTER}")  # 模拟发送enter，点击确定
                        self.wait(1)
                break

            self.wait(1)
            count -= 1

        temp_path = tempfile.mktemp(suffix=".csv")
        set_foreground(self._app.top_window())

        # alt+s保存，alt+y替换已存在的文件
        self._app.top_window().Edit1.set_edit_text(temp_path)
        self.wait(0.1)
        self._app.top_window().type_keys("%{s}%{y}", set_foreground=False)
        # Wait until file save complete otherwise pandas can not find file
        self.wait(0.2)
        if self.is_exist_pop_dialog():
            self._app.top_window().Button2.click()
            self.wait(0.2)

        return self._format_grid_data(temp_path)

    def _click(self, control_id):
        """
        鼠标点击指定控件
        """
        btn = self._app.top_window().child_window(control_id=control_id, class_name="Button")
        btn.click()

    def _click_grid_by_row(self, row):
        x = config.COMMON_GRID_LEFT_MARGIN
        y = config.COMMON_GRID_FIRST_ROW_HEIGHT + config.COMMON_GRID_ROW_HEIGHT * row

        self._app.top_window().child_window(
            control_id=config.COMMON_GRID_CONTROL_ID,
            class_name="CVirtualGridCtrl",
        ).click(coords=(x, y))

    def apply_stocks(self):
        stock_list = self.spider.get_today_stock()

        if len(stock_list) == 0:
            return "今日无新股"

        ret = ""
        set_foreground(self._main)
        self._switch_left_menus(config.AUTO_IPO_MENU_PATH)

        new_stocks = []
        for stock in stock_list:
            stock_id = stock['id']
            stock_name = stock['name']
            stock_price = stock['price']
            self._type_edit_control_keys(control_id=config.TRADE_SECURITY_CONTROL_ID, text=stock_id)
            self.wait(1)

            apply_num = self._main.child_window(control_id=0x3FA, class_name="Static").window_text()
            if not apply_num or int(apply_num) == 0:
                set_foreground(self._main)
                self._main.child_window(control_id=config.TRADE_REFILL_CONTRON_ID, class_name="Button").click()
                self.wait(1)
                ret += "%s 可申购数量: %s; " % (stock_name, 0)
                continue

            new_stocks.append([stock_id, stock_name, stock_price, apply_num])
            self.wait(1)

        ret += '\n'
        for stock_id, stock_name, stock_price, apply_num in new_stocks:
            self.buy(stock_id, stock_price, apply_num)
            ret += "%s 申购成功， 申购数量: %s; " % (stock_name, apply_num)
            self.wait(1)

        return ret


if __name__ == '__main__':
    from config import ths_xiadan_path

    ths = THSTrader(ths_xiadan_path)
    ths.apply_stocks()
