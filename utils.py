# -*- encoding: utf-8 -*-

import os
import logging

logger = logging.getLogger("auto_make_money")
logger.setLevel(logging.DEBUG)
logger.propagate = False

fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(filename)s %(lineno)s: %(message)s"
)

# 日志输出到控制台
sh = logging.StreamHandler()
sh.setFormatter(fmt)

# 日志输出到文件
log_file = "logs/auto_make_money.log"
os.makedirs(os.path.dirname(log_file), exist_ok=True)
fh = logging.FileHandler(log_file, mode='a', encoding='utf-8')
fh.setFormatter(fmt)

logger.handlers.append(sh)
logger.handlers.append(fh)
