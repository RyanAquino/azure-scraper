"""
Set scrape configurations
"""
import os

from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("base_url")
BACKLOG_ENDPOINT = os.getenv("backlog_endpoint")
EMAIL = os.getenv("email")
PASSWORD = os.getenv("password")
BINARY_PATH_LOCATION = os.getenv("binary_path_location")
WORK_ITEM_ENDPOINT = os.getenv("work_item_endpoint")
max1 = os.getenv("max_retries")
MAX_RETRIES = int(0 if max1 is None else max1)
max2 = os.getenv("max_wait_time")
MAX_WAIT_TIME = int(0 if max2 is None else max2)
ON_PREM = os.getenv("on_prem", "false").lower() == "true"
