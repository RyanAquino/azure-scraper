"""
Set scrape configurations
"""
from dotenv import load_dotenv
import os


load_dotenv()
BASE_URL = os.getenv('base_url')
BACKLOG_ENDPOINT = os.getenv('backlog_endpoint')
EMAIL = os.getenv('email')
PASSWORD = os.getenv('password')
BINARY_PATH_LOCATION = os.getenv('binary_path_location')
WORK_ITEM_ENDPOINT = os.getenv('work_item_endpoint')
MAX_RETRIES = os.getenv('max_retries')
MAX_WAIT_TIME = os.getenv('max_wait_time')
