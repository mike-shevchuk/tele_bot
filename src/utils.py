from pathlib import Path
import pandas as pd
import requests

root_prj = Path(__file__).parent.parent.absolute()


def get_reg_users():
    reg_user_path = root_prj / 'data/reg_user.csv'
    print(f'{reg_user_path.parent=}')
    reg_user_path.parent.mkdir(parents=True, exist_ok=True)

    if reg_user_path.is_file():
        df = pd.read_csv(reg_user_path)
        print('Exist')
        return df
    else:
        print('not exist')
        res = pd.DataFrame()
        res.to_csv(reg_user_path)
        return res
        
    # STEP_1: check if file exist
    # if 
    # STEP_2: if not create empty file and return empyy dataframe
    # STEP3: if exist, read csv dile and return DataFrame
    ...


def save_reg_user(df):
    reg_user_path = root_prj / 'data/reg_user.csv'
    df.to_csv(reg_user_path)





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