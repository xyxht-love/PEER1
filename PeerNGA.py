import os
import requests  # 新增：用于处理下载
from selenium import webdriver  # 直接使用标准 selenium
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from typing import NoReturn

# 假设 IO 模块仍然可用，或可将其功能直接移入
# from IO import unZip, downloader 

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
    def __init__(self, driverPath: str) -> NoReturn:
        # 1. 使用标准 selenium 的 Options
        options = webdriver.ChromeOptions()
        options.add_argument('--incognito')
        # 关键：设置下载路径，避免弹窗，让浏览器自动下载
        prefs = {'download.default_directory': os.path.abspath('./downloads')}
        options.add_experimental_option('prefs', prefs)

        # 2. 使用标准 selenium 的 Chrome，正确传入 service 和 options
        self.browser = webdriver.Chrome(service=Service(driverPath), options=options)
        
        # 移除原有的 request_interceptor 相关代码
        self.states = {
            "sign in": False,
            'enter database': False,
            'search records': False
        }
        # 用于存储当前页面的 cookies，供 requests 使用
        self.cookies = {}

    def signIn(self, email: str, password: str) -> NoReturn:
        self.browser.get('https://ngawest2.berkeley.edu/users/sign_in?unauthenticated=true')

        inputEmail = self.browser.find_element(By.NAME, 'user[email]')
        inputPassword = self.browser.find_element(By.NAME, 'user[password]')
        inputEmail.send_keys(email)
        inputPassword.send_keys(password)
        btnSignIn = self.browser.find_element(By.NAME, 'commit')
        btnSignIn.click()
        
        # 等待登录完成并更新 cookies
        WebDriverWait(self.browser, 10).until(lambda x: x.find_element(By.CLASS_NAME, 'alert'))
        parAlert = self.browser.find_element(By.CLASS_NAME, 'alert')
        alert = parAlert.text

        if alert != '':
            print(alert)
        else:
            print('Signed in successfully.')
            self.states['sign in'] = True
            # 更新 cookies 供 requests 使用
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
        # 1. 点击下载按钮，触发下载流程
        self.browser.execute_script('getSelectedResult(true)')
        
        # 处理可能弹出的两个确认框
        for _ in range(2):
            try:
                alert = self.browser.switch_to.alert
                alert.accept()
            except:
                break
        
        # 2. 从浏览器获取最终的下载链接
        # 方法：监听网络请求较复杂，这里改为从页面源码或控制台尝试获取
        # 更稳健的方法：检查页面变化或使用 devtools 协议，但实现复杂。
        # 替代方案：利用浏览器的下载功能，自动下载到指定目录。
        # 由于我们设置了 'download.default_directory'，文件会自动保存。
        # 但我们需要知道文件名。
        
        # 简单起见，我们从页面中查找可能存在的下载链接（这是最可能失败的地方）
        # 在实际使用中，可能需要更复杂的逻辑来捕获下载链接。
        # 这里提供一个示例，假设下载链接会出现在一个隐藏的 input 或 a 标签中。
        try:
            # 示例：尝试从某个元素获取下载链接（需要根据实际网页调整）
            download_link_element = self.browser.find_element(By.CSS_SELECTOR, 'a[href*="download"]')
            download_url = download_link_element.get_attribute('href')
        except:
            # 如果找不到，则打印提示，需要您根据实际网页结构补充
            print("无法自动获取下载链接，请检查网页元素。")
            return
        
        # 3. 使用 requests 下载文件
        if download_url:
            # 使用之前保存的 cookies 创建会话
            session = requests.Session()
            session.cookies.update(self.cookies)
            
            # 发送请求，流式下载
            response = session.get(download_url, stream=True)
            if response.status_code == 200:
                # 确保保存目录存在
                os.makedirs(saveDir, exist_ok=True)
                save_path = os.path.join(saveDir, 'downloaded_records.zip')
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"文件已下载至: {save_path}")
                
                # 如果存在解压函数，可以调用
                # from IO import unZip
                # unZip(save_path, saveDir)
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

    # 移除原有的 __interceptor 方法
