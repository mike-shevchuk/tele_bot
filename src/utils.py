from pathlib import Path
import pandas as pd
import requests
import os
import loguru
import time

import numpy as np

from src.Users import UserTele
from src.Errors import CSVError


root_prj = Path(__file__).parent.parent.absolute()


def pydantic2pandas(user):
    user_df = pd.DataFrame([user.to_dict()])
    user_df = user_df.replace({np.nan: None})
    user_df.set_index('id', inplace=True)
    return user_df


def pandas2pydentic(user_df):
    user_id = int(user_df.index[0])
    user_dct = user_df.to_dict(orient='records')[0]
    user_dct['id'] = user_id

    user_tele : UserTele = UserTele.model_validate(user_dct)

    return user_tele


def create_empty_csv():
    us_test = UserTele.get_example()
    t_id = us_test.id
    user_df = pydantic2pandas(us_test)
    user_df = user_df.drop([t_id])
    save_reg_user(user_df)
    return user_df


def get_user_by_id(usr_id):
    users_reg_df: pd.DataFrame  = get_reg_users()

    if usr_id in users_reg_df.index:
        logger.debug(f'User {usr_id} is already registered ')
        return users_reg_df.loc[[usr_id]]
    else:
        logger.debug(f'User {usr_id} not in db')
        return pd.DataFrame()


def get_reg_users():
    reg_user_path = root_prj / 'data/reg_user.csv'
    print(f'{reg_user_path.parent=}')
    reg_user_path.parent.mkdir(parents=True, exist_ok=True)

    if reg_user_path.is_file():
        df = pd.read_csv(reg_user_path)
        if df.empty:     
            logger.waring('Csv file is empty')
            return create_empty_csv()
        
        df= df.replace({np.nan: None})
        df.set_index('id', inplace=True)
        return df
    else:
        logger.warning('not exist')
        return create_empty_csv()
        
    # STEP_1: check if file exist
    # if 
    # STEP_2: if not create empty file and return empyy dataframe
    # STEP3: if exist, read csv dile and return DataFrame
    ...


def save_reg_user(df):
    reg_user_path = root_prj / 'data/reg_user.csv'
    df.to_csv(reg_user_path)



def setup_logger(LOGGER: loguru.logger, data_name="", log_dir=""):
    # Set up loguru
    timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
    logfile_name = f'tele_bot_{data_name}'
    dir_logs = f"logs/{log_dir}"
    logfile_name = f"{dir_logs}/{logfile_name}_{timestr}.log"
    fmt = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {name} | <level>{level}</level> | <level>{message}</level>"
    LOGGER.remove(0)
    LOGGER.add(logfile_name, level="DEBUG", format=fmt, colorize=False, backtrace=False, diagnose=True)
    LOGGER.add(os.sys.stdout, level="TRACE", format=fmt, colorize=True, backtrace=True, diagnose=True)

    global logger
    logger = LOGGER
    return logger



def expand_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.url
    except requests.RequestException as e:
        # logger.exception(f"Error expanding URL: {e}")
        return url


def human_readable(file_size, unit='B'):
    if file_size > 1024 * 1024:
        file_size /=  1024 * 1024
        unit = 'MB'
    elif file_size > 1024:
        file_size /= 1024
        unit = 'KB'
    return f"{file_size:.2f} {unit}"



def delete_video_file(file_path):
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"The file {file_path} has been deleted successfully.")
        else:
            logger.warning(f"The file {file_path} does not exist.")
    except Exception as e:
        logger.error(f"An error occurred while trying to delete the file {file_path}: {e}")


def get_file_size(file_path):
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            # Get the size of the file in bytes
            file_size = os.path.getsize(file_path)
            logger.info(f"The size of the file {file_path} is {file_size} bytes.")
            return file_size
        else:
            logger.warning(f"The file {file_path} does not exist.")
            return None
    except Exception as e:
        logger.error(f"An error occurred while trying to get the size of the file {file_path}: {e}")
        return None