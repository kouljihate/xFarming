import os
import logging

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)


class TestLogger:
    def __init__(self, name):
        log_file = os.path.join(LOG_DIR, f'{name}.log')
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self.logger.addHandler(handler)
        self.info(f"=== Test Log Started: {name} ===")

    def info(self, msg):
        self.logger.info(msg)

    def step(self, msg):
        self.info(f"STEP: {msg}")

    def done(self, msg=''):
        self.info(f"=== Test Log Ended{f' - {msg}' if msg else ''} ===")
        for h in self.logger.handlers:
            h.flush()
