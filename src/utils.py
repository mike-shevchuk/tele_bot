from pathlib import Path
import pandas as pd
import requests
import os
import loguru
import time
import yaml
from easydict import EasyDict as edict
from srtools import cyrillic_to_latin, latin_to_cyrillic
import numpy as np
import re
from src.Users import UserTele, Level
from src.Errors import CSVError


root_prj = Path(__file__).parent.parent.absolute()

# get name or nickname from username or full_name something that exists in db
def get_name_from_pydantic(user: UserTele):
    username = user.username
    full_name = user.full_name
    if username:
        return username
    elif full_name:
        return full_name
    else:
        return user.id

def crt_cfg_params(cfg_params):
    cfg = load_config('configs/cfg.yml')
    cfg_params_copy = edict(cfg_params.copy())
    res = edict()
    for key, value in cfg_params_copy.items():
        keys = key.split('.')
        nested_dict = reduce(lambda d, key: d.get(key) if d else None, keys[:-1], cfg)
        if nested_dict:
            cfg_value = nested_dict.get(keys[-1])
            if value is None:
                value = cfg_value
        curr_dict = res
        for i, k in enumerate(keys):
            if k not in curr_dict:
                curr_dict[k] = {} if i < len(keys) - 1 else value
            curr_dict = curr_dict[k]
    return res


def load_config(config_path='configs/cfg.yml'):
    """
    Load configuration from a YAML file.

    Args:
        config_path (str): Path to the YAML configuration file.

    Returns:
        dict: Configuration data from the YAML file.
    """
    with open(config_path) as file:
        config = yaml.safe_load(file)
    config = edict(config)

    shared_vars = config.shared_vars
    shared_vars.update({'prj_root': os.getcwd()})
    parse_config(config, shared_vars=shared_vars)
 

    # shared_vars = config.shared_vars
    # TODO: change this hack
    # prj_root = str(Path(file).parent.parent)
    # shared_vars.update({'prj_root': os.path.normpath(prj_root)})
    # parse_config(config, shared_vars=shared_vars)
    
    return config


def parse_config(cfg, shared_vars):
    # TODO: check is str a path is path normalizete it
    for key, value in cfg.items():
        if isinstance(value, dict):
            parse_config(value, shared_vars)
        elif isinstance(value, str):
            new_value = value
            for var, val in shared_vars.items():
                if f"{{{var}}}" in value:
                    new_value = new_value.replace(f"{{{var}}}", str(val))
            # if new value is numeric
            if new_value.isnumeric():
                new_value = int(new_value)
                
            cfg[key] = new_value
 

def pydantic2pandas(user):
    user_df = pd.DataFrame([user.to_dict()])
    user_df = user_df.replace({np.nan: None})
    user_df.set_index('id', inplace=True)
    return user_df


def pandas2pydentic(user_df):
    user_id = int(user_df.index[0])
    user_dct = user_df.to_dict(orient='records')[0]
    user_dct['id'] = user_id 
    user_dct['level'] = Level.__members__.get((user_dct['level']).split('.')[-1])

    user_tele : UserTele = UserTele.model_validate(user_dct)

    return user_tele


def create_empty_csv():
    us_test = UserTele.get_example()
    t_id = us_test.id
    user_df = pydantic2pandas(us_test)
    user_df = user_df.drop([t_id])
    save_reg_user(user_df)
    return user_df

def remove_non_ascii(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def get_user_by_id(usr_id):
    users_reg_df: pd.DataFrame  = get_reg_users()

    if usr_id in users_reg_df.index:
        logger.debug(f'User {usr_id} is already registered ')
        return users_reg_df.loc[[usr_id]]
    else:
        logger.debug(f'User {usr_id} not in db')
        return pd.DataFrame()


def update_row(user:UserTele):
    all_df = get_reg_users()
    user_row = pydantic2pandas(user)
    logger.trace(f'{all_df=}, \n{user_row=}')
    all_df.update(user_row)
    save_reg_user(all_df)


def get_reg_users():
    reg_user_path = root_prj / 'data/reg_user.csv'
    print(f'{reg_user_path.parent=}')
    reg_user_path.parent.mkdir(parents=True, exist_ok=True)

    if reg_user_path.is_file():
        df = pd.read_csv(reg_user_path)
        if df.empty:     
            logger.warning('Csv file is empty')
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
    LOGGER.add(logfile_name,
                level="DEBUG",
                format=fmt,
                colorize=False,
                backtrace=False,
                diagnose=True)
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


def h_readable(file_size, unit='B'):
    if file_size > 1024 * 1024:
        file_size /=  1024 * 1024
        unit = 'MB'
    elif file_size > 1024:
        file_size /= 1024
        unit = 'KB'
    return f"{file_size:.2f} {unit}" if file_size > 0 else f'0 {unit} or less'



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


def cr_2_ln(sent:str) -> str:
    return cyrillic_to_latin(sent)

def ln_2_cr(sent: str) -> str:
    return latin_to_cyrillic(sent)

def is_ltn(sent:str) -> bool:
    return sent == sent.encode('utf-8')

def get_prj_root():
    root_path = Path.cwd()
    return root_path

