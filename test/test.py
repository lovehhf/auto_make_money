
import pywinauto
from pywinauto.win32functions import SetForegroundWindow, ShowWindow


exe_path = r"C:\同花顺软件\同花顺\xiadan.exe"
app = pywinauto.Application().connect(path=exe_path, timeout=10)
main = app.top_window()
# print(main.window_text())
SetForegroundWindow(main.wrapper_object())


if app.top_window().window(class_name="Static", title_re=".*输入验证码.*"):
    win = app.top_window().window(class_name="Static", control_id=0x965)

    print(win.exists())
    win.capture_as_image().save("test.png")
    print(win.rectangle())
    win.print_control_identifiers()

# win = app.top_window().window(class_name="Static", control_id=0x965)
# print(win.exists())
# win.print_control_identifiers()