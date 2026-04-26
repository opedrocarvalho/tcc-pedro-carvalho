import os
import sys
import logging
from pathlib import Path
from datetime import datetime

class Config:
    
    BASE_DIR = Path("/app")
    DATA_DIR = BASE_DIR / "data"
    DUCKDB_DIR = DATA_DIR / "duckdb"
    LOGS_DIR = BASE_DIR / "logs"
    

    DUCKDB_PATH = DUCKDB_DIR / "destinosbrasil.duckdb"
    DATA_EXTRACAO = datetime.now().strftime("%Y-%m-%d")

    CHROME_OPTIONS = [
        "--start-maximized",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--no-zygote",
        "--disable-extensions",
        "--disable-plugins-discovery",
        "--disable-images",
    ]


    HEADLESS = True

    DEFAULT_TIMEOUT = 30
    PAGE_LOAD_TIMEOUT = 60
    
    @classmethod
    def ensure_directories(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.DUCKDB_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)

config = Config()
config.ensure_directories()


def setup_logging(name, level=logging.INFO):
    log_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    log_file_path = config.LOGS_DIR / f"{name}.log"
    
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    logger.propagate = False 
    return logger