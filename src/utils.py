from pathlib import Path
import pandas as pd
import requests
import os
import loguru
import time
import numpy as np


from src.UserTele import UserTele
from src.ExceptionClass import CSVError


root_prj = Path(__file__).parent.parent.absolute()


def pydantic2pandas(user):
    user_df = pd.DataFrame([user.to_dict()]).set_index(['id'])
    return user_df


def pandas2pydentic(user_df):
    user_id = int(user_df.index[0])
    user_dct = user_df.to_dict(orient='records')[0]
    user_dct['id'] = user_id

    user_tele : UserTele = UserTele.model_validate(user_dct)
    return user_tele

def get_reg_users():
    reg_user_path = root_prj / 'data/reg_user.csv'
    empty_df = pd.DataFrame()
    print(f'{reg_user_path.parent=}')

    reg_user_path.parent.mkdir(parents=True, exist_ok=True)

    if reg_user_path.is_file():
        df = pd.read_csv(reg_user_path)
        if df.empty:
            logger.warning('CSV EMPTY')
            return empty_df
        
        df = df.replace([np.nan], [None], regex=False)
        df.set_index('id', inplace=True)
        logger.trace('Exist csv')
        return df
    else:
        logger.warning('not exist csv')
        # res = pd.DataFrame().reset_index(drop=True)
        # res = res.replace([np.nan], [None], regex=False)
        # res.to_csv(reg_user_path)
        raise CSVError
        
    # STEP_1: check if file exist
    # if 
    # STEP_2: if not create empty file and return empyy dataframe
    # STEP3: if exist, read csv dile and return DataFrame
    ...


def get_user_by_id(u_id):
    users_reg_df: pd.DataFrame  = get_reg_users()

    if users_reg_df.empty:
        raise CSVError
    
    # if len(users_reg_df) < 1:
    #     raise CSVError    

    if u_id in users_reg_df.index:
        usr_temp = users_reg_df.loc[[u_id]]
        logger.debug(f'User {u_id} is already registered ')
        user_tele = pandas2pydentic(usr_temp)
        # user_dct = usr_temp.to_dict(orient='records')[0]
        # user_dct['id'] = u_id

        # user_tele : UserTele = UserTele.model_validate(user_dct)
        return user_tele

    else:
        logger.warning(f'User is not in db {u_id}')
        return pd.DataFrame()


def save_reg_user(df):
    reg_user_path = root_prj / 'data/reg_user.csv'
    df.to_csv(reg_user_path, index=False)


def update_reg_user(user: UserTele):
    reg_user_df = get_reg_users()

    user_df = pydantic2pandas(user)
    reg_user_df.loc[[user.id]] = user_df

    save_reg_user(reg_user_df)
    logger.info(f'Update info about user {user.id}')

def reg_user_db(usr_tele):
    df = pydantic2pandas(usr_tele)
    # df = pd.DataFrame([usr_tele.to_dict()])    
    try:
        users_reg_df: pd.DataFrame  = get_reg_users()
    except CSVError as e:
        logger.warning('db is not exist add new user {usr_tele.id}')
        all_df = df
        save_reg_user(df)
        return 
    except Exception as e:
        raise e


    if users_reg_df.empty:
        logger.warning('db is empty add new user {usr_tele.id}')
        # save_reg_user(df)
        all_df = df
    else:
        all_df = pd.concat([users_reg_df, df]).reset_index(drop=True)

    logger.debug(f'Add new user {usr_tele.id} ')

    save_reg_user(all_df)

    



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