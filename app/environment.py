import os

from dotenv import dotenv_values

ROOT_DIR = os.getcwd()


def get_app_config():
    if ".env.local" in os.listdir():
        return dotenv_values(ROOT_DIR + "/.env.local")
    else:
        return dotenv_values(ROOT_DIR + "/.env")


APP_CONFIG = get_app_config()
