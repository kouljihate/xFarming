import os
import sys
import logging
import traceback

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'


class TestLogger:
    def __init__(self, name):
        log_file = os.path.join(LOG_DIR, f'{name}.log')
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self.logger.addHandler(handler)
        self._console('', f"{BOLD}===== {name} ====={RESET}")
        self.info(f"=== Test Log Started: {name} ===")

    def _console(self, color, msg):
        line = f"{color}{msg}{RESET}" if color else msg
        try:
            safe = line.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
            print(safe, file=sys.stdout, flush=True)
        except Exception:
            pass

    def info(self, msg):
        self.logger.info(msg)
        self._console('', f"  {msg}")

    def ok(self, msg):
        self.logger.info(f"OK: {msg}")
        self._console(GREEN, f"  ✓ {msg}")

    def step(self, msg):
        self.logger.info(f"STEP: {msg}")
        self._console(CYAN, f"\n{'='*60}\n  STEP: {msg}\n{'='*60}")

    def error(self, msg, exc_info=None):
        self.logger.error(msg)
        self._console(RED, f"  ✗ ERROR: {msg}")
        if exc_info:
            tb = ''.join(traceback.format_exception(*exc_info))
            self.logger.error(tb)
            for line in tb.strip().split('\n'):
                self._console(RED, f"    {line}")

    def done(self, msg=''):
        self.info(f"=== Test Log Ended{f' - {msg}' if msg else ''} ===")
        color = GREEN if 'PASSED' in msg else RED
        self._console(color, f"{BOLD}{'='*60}\n  {msg}\n{'='*60}{RESET}\n")
        for h in self.logger.handlers:
            h.flush()
