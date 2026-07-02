import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from typing import NoReturn


def _checkStates(level: int):
    def decorator(func):
        def check(self, *args, **kwargs):
            stateNames = list(self.states.keys())
            for i in range(level):
                stateName = stateNames[i]
                if not self.states[stateName]:
                    print('Please {0} before {1}.'.format(stateName, func.__name__))
                    return
            return func(self, *args, **kwargs)
        return check
    return decorator


class PeerNGA:
    # 修改点1：将 driverPath 设为可选参数，默认值为 None
    def __init__(self, driverPath: str = None) -> NoReturn:
        options = webdriver.ChromeOptions()
        options.add_argument('--incognito')
        prefs = {'download.default_directory': os.path.abspath('./downloads')}
        options.add_experimental_option('prefs', prefs)

        # 修改点2：智能处理驱动路径
        if driverPath:
            # 如果传入了路径，使用指定的驱动
            self.browser = webdriver.Chrome(service=Service(driverPath), options=options)
        else:
            # 如果未传入路径，让 Selenium Manager 自动下载和管理驱动
            self.browser = webdriver.Chrome(options=options)
        
        self.states = {
            "sign in": False,
            'enter database': False,
            'search records': False
        }
        self.cookies = {}

    def signIn(self, email: str, password: str) -> NoReturn:
        self.browser.get('https://ngawest2.berkeley.edu/users/sign_in?unauthenticated=true')

        inputEmail = self.browser.find_element(By.NAME, 'user[email]')
        inputPassword = self.browser.find_element(By.NAME, 'user[password]')
        inputEmail.send_keys(email)
        inputPassword.send_keys(password)
        btnSignIn = self.browser.find_element(By.NAME, 'commit')
        btnSignIn.click()
        
        WebDriverWait(self.browser, 10).until(lambda x: x.find_element(By.CLASS_NAME, 'alert'))
        parAlert = self.browser.find_element(By.CLASS_NAME, 'alert')
        alert = parAlert.text

        if alert != '':
            print(alert)
        else:
            print('Signed in successfully.')
            self.states['sign in'] = True
            self.cookies = {c['name']: c['value'] for c in self.browser.get_cookies()}

    def close(self) -> NoReturn:
        self.browser.quit()

    @_checkStates(1)
    def enterDB(self, label: str):
        DBdict = {
            'NGA West2': 1,
            'NGA east': 2
        }
        self.browser.get('https://ngawest2.berkeley.edu/spectras/new?sourceDb_flag={0}'.format(DBdict[label]))
        self.browser.execute_script('OnSubmit()')
        WebDriverWait(self.browser, 10).until(lambda x: x.find_element(By.NAME, "search[search_nga_number]"))
        self.states['enter database'] = True

    @_checkStates(2)
    def search(self, settings: dict = None):
        if settings:
            for label in settings:
                elemName = self.__getElemName(label)
                if elemName:
                    inputElem = self.browser.find_element(By.NAME, elemName)
                    inputElem.send_keys(settings[label])

        if self.__clickBtnSearch():
            self.states['search records'] = True
            return True
        return False

    @_checkStates(3)
    def download(self, saveDir: str):
        self.browser.execute_script('getSelectedResult(true)')
        
        for _ in range(2):
            try:
                alert = self.browser.switch_to.alert
                alert.accept()
            except:
                break
        
        try:
            download_link_element = self.browser.find_element(By.CSS_SELECTOR, 'a[href*="download"]')
            download_url = download_link_element.get_attribute('href')
        except:
            print("无法自动获取下载链接，请检查网页元素。")
            return
        
        if download_url:
            session = requests.Session()
            session.cookies.update(self.cookies)
            
            response = session.get(download_url, stream=True)
            if response.status_code == 200:
                os.makedirs(saveDir, exist_ok=True)
                save_path = os.path.join(saveDir, 'downloaded_records.zip')
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"文件已下载至: {save_path}")
            else:
                print(f"下载失败，状态码: {response.status_code}")

    def __clickBtnSearch(self) -> bool:
        self.browser.execute_script('OnSubmit()')
        divNotice = WebDriverWait(self.browser, 10).until(lambda x: x.find_element(By.ID, 'notice'))
        notice = divNotice.text
        print(notice)
        if ' NO ' in notice or ' exceed ' in notice:
            return False
        return True

    @staticmethod
    def __getElemName(label: str):
        nameDict = {
            'RSNs': 'search[search_nga_number]',
            'Event Name': 'search[search_eq_name]',
            'Station Name': 'search[search_station_name]',
            'Fault Type': 'search[faultType]',
            'Magnitude': 'search[magnitude]',
            'R_JB': 'search[rjb]',
            'R_rup': 'search[rrup]',
            'Vs30': 'search[vs30]',
            'D5-95': 'search[duration]',
            'Pulse': 'search[pulse]',
            'Max No. Records': 'search[output_num]'
        }
        if label in nameDict:
            return nameDict[label]
        print('There is no such setting item: {0}'.format(label))
        return False
