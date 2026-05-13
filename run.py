from app.utils import logging
import sys
import os
from icecream import ic

log_mode = 'file'
if len(sys.argv) > 1:
    if '--debug-console' in sys.argv:
        log_mode = 'console'
    elif '--debug-file' in sys.argv:
        log_mode = 'file'

os.environ['LOG_MODE'] = log_mode

from app import create_app
from app.database import init_db

app = create_app()

if __name__ == '__main__':
    try:
        with app.app_context():
            init_db()
        logging.log_message('info', f"Starting SmartFarmerFlow in {log_mode} mode...")
        app.run(debug=True, port=5001)
    except Exception as e:
        app.logger.error(f"Application error: {e}")
    except KeyboardInterrupt:
        app.logger.info("SmartFarmerFlow stopped by user")