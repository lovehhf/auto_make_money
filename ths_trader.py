# -*- encoding: utf-8 -*-
"""
同花顺通用wrapper 来自easytrader
link： https://github.com/shidenggui/easytrader
"""

import abc
import time
import re
import functools
import tempfile
import pandas as pd
import pywinauto
from pywinauto import win32defines, findwindows, timings
from pywinauto.win32functions import SetForegroundWindow, ShowWindow
from io import StringIO

import config
from utils.log import logger
from utils.captcha import captcha_recognize
from typing import Optional


class TradeError(IOError):
    pass


def get_code_type(code):
    """
    判断代码是属于那种类型，目前仅支持 ['fund', 'stock']
    :return str 返回code类型, fund 基金 stock 股票
    """
    if code.startswith(('00', '30', '60')):
        return 'stock'
    return 'fund'


def set_foreground(window):
    if window.has_style(win32defines.WS_MINIMIZE):  # if minimized
        ShowWindow(window.wrapper_object(), 9)  # restore window state
    else:
        SetForegroundWindow(window.wrapper_object())  # bring to front


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


class PopDialogHandler:
    def __init__(self, app):
        self._app = app

    @staticmethod
    def handle(self, title):
        if any(s in title for s in {"提示信息", "委托确认", "网上交易用户协议", "撤单确认"}):
            self._submit_by_shortcut()
            return None

        if "提示" in title:
            content = self._extract_content()
            self._submit_by_click()
            return {"message": content}

        content = self._extract_content()
        self._close()
        return {"message": "unknown message: {}".format(content)}

    def _extract_content(self):
        return self._app.top_window().Static.window_text()

    @staticmethod
    def _extract_entrust_id(content):
        return re.search(r"[\da-zA-Z]+", content).group()

    def _submit_by_click(self):
        try:
            self._app.top_window()["确定"].click()
        except Exception as ex:
            self._app.Window_(best_match="Dialog", top_level_only=True).ChildWindow(
                best_match="确定"
            ).click()

    def _submit_by_shortcut(self):
        set_foreground(self._app.top_window())
        self._app.top_window().type_keys("%Y", set_foreground=False)

    def _close(self):
        self._app.top_window().close()


class TradePopDialogHandler(PopDialogHandler):
    def handle(self, title) -> Optional[dict]:
        if title == "委托确认":
            self._submit_by_shortcut()
            return None

        if title == "提示信息":
            content = self._extract_content()
            if "超出涨跌停" in content:
                self._submit_by_shortcut()
                return None

            if "委托价格的小数价格应为" in content:
                self._submit_by_shortcut()
                return None

            if "逆回购" in content:
                self._submit_by_shortcut()
                return None

            if "正回购" in content:
                self._submit_by_shortcut()
                return None

            return None

        if title == "提示":
            content = self._extract_content()
            if "成功" in content:
                entrust_no = self._extract_entrust_id(content)
                self._submit_by_click()
                return {"entrust_no": entrust_no}

            self._submit_by_click()
            time.sleep(0.05)
            raise TradeError(content)
        self._close()
        return None


class BaseTrader(abc.ABC):
    def __init__(self):
        pass

    def connect(self, exe_path: str):
        pass

    def buy(self, stock_id: str, price, amount):
        pass


class THSTrader(BaseTrader):
    def __init__(self, exe_path):
        super().__init__()
        self.connect(exe_path)

    def connect(self, exe_path: str):
        self._app = pywinauto.Application().connect(path=exe_path, timeout=10)
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

    def buy_bonds(self, bonds):
        """
        申购可转债
        """
        price, amount = 100, 10000

        ret = {}
        for i in range(1, config.ACCOUNT_COUNT + 1):
            self._main.set_focus()

            key = '%%%s' % i
            pywinauto.keyboard.send_keys(key)
            self.wait(2)

            # pyautogui.hotkey('alt', '%s' % i)
            # self.wait(2)

            name = self.get_account_name()
            logger.info("press alt + %s to switch account to: %s" % (i, name))

            buy_ret = ''
            # for bond_id in bonds:
            #     buy_ret += str(self.buy(bond_id, price, amount)) + "\n"
            #     self.wait(2)

            self.auto_ipo()

            ret[name] = buy_ret
            self.wait(1)

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
        return self._handle_pop_dialogs(
            handler_class=TradePopDialogHandler
        )

    def _set_trade_params(self, security, price, amount):
        """
        设置交易参数
        """
        code = security[-6:]
        logger.info("set_trade_params，code: %s, price: %s, amount: %s" % (security, price, amount))
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
        editor.type_keys(text)

    def _submit_trade(self):
        time.sleep(0.2)
        self._main.child_window(
            control_id=config.TRADE_SUBMIT_CONTROL_ID, class_name="Button"
        ).click()

    def _handle_pop_dialogs(self, handler_class=PopDialogHandler):
        """
        处理弹出的窗口
        """
        cnt = 0
        while self.is_exist_pop_dialog():
            pywinauto.keyboard.send_keys('{ENTER}')
            logger.info("exist_pop_dialog, press enter.")
            self.wait(1)
            cnt += 1
            if cnt >= 2:
                self._main.set_focus()
                break

        return {"message": "success"}

    def is_exist_pop_dialog(self):
        self.wait(0.5)  # wait dialog display
        try:
            main_wrapper = self._main.wrapper_object()
            top_window_wrapper = self._app.top_window().wrapper_object()
            ret = main_wrapper != top_window_wrapper
            if ret:
                print(main_wrapper, top_window_wrapper)
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
            encoding = "gbk"
        )
        return df.to_dict("records")

    def _get_grid_data(self, control_id):
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
        self._app.top_window().child_window(
            control_id=control_id, class_name="Button"
        ).click()

    def _click_grid_by_row(self, row):
        x = config.COMMON_GRID_LEFT_MARGIN
        y = config.COMMON_GRID_FIRST_ROW_HEIGHT + config.COMMON_GRID_ROW_HEIGHT * row

        self._app.top_window().child_window(
            control_id=config.COMMON_GRID_CONTROL_ID,
            class_name="CVirtualGridCtrl",
        ).click(coords=(x, y))

    def auto_ipo(self):
        self._switch_left_menus(config.AUTO_IPO_MENU_PATH)

        stock_list = self._get_grid_data(config.COMMON_GRID_CONTROL_ID)

        if len(stock_list) == 0:
            return {"message": "今日无新股"}

        invalid_list_idx = [
            i for i, v in enumerate(stock_list) if v[config.AUTO_IPO_NUMBER] <= 0
        ]

        if len(stock_list) == len(invalid_list_idx):
            return {"message": "没有发现可以申购的新股"}

        self._click(config.AUTO_IPO_SELECT_ALL_BUTTON_CONTROL_ID)
        self.wait(0.1)

        for row in invalid_list_idx:
            self._click_grid_by_row(row)
        self.wait(0.1)

        self._click(config.AUTO_IPO_BUTTON_CONTROL_ID)
        self.wait(0.1)

        return self._handle_pop_dialogs()


if __name__ == '__main__':
    from config import ths_xiadan_path

    ths = THSTrader(ths_xiadan_path)
    ths.buy_bonds(["113634", "111002"])

    # from utils.stock import get_today_ipo_data
    # ipo_data = get_today_ipo_data()
    # print(ipo_data)
