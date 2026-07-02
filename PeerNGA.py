import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from IO import unZip, downloader
from typing import NoReturn


def _checkStates(level: int):
    def decorator(func):
        def check(self, *args, **kwargs):
            stateNames = list(self.states.keys())
            for i in range(level):
                stateName = stateNames[i]
                if not self.states[stateName]:
                    print('Please {0} before {1}.'.format(stateName, func.__name__))
                    return check
            return func(self, *args, **kwargs)
        return check
    return decorator


class PeerNGA:
    def __init__(self, driverPath: str = None) -> NoReturn:
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if driverPath:
            service = Service(driverPath)
            self.browser = webdriver.Chrome(service=service, options=options)
        else:
            self.browser = webdriver.Chrome(options=options)  # Selenium Manager 自动找驱动

        self.states = {
            "sign in": False,
            "enter database": False,
            "search records": False
        }

    def signIn(self, email: str, password: str) -> NoReturn:
        self.browser.get("https://ngawest2.berkeley.edu/users/sign_in")

        # 等待页面加载完成
        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.NAME, "user[email]"))
        )

        inputEmail = self.browser.find_element(By.NAME, "user[email]")
        inputPassword = self.browser.find_element(By.NAME, "user[password]")
        inputEmail.send_keys(email)
        inputPassword.send_keys(password)

        btnSignIn = self.browser.find_element(By.NAME, "commit")
        btnSignIn.click()

        # 等待登录结果
        try:
            WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "alert"))
            )
            parAlert = self.browser.find_element(By.CLASS_NAME, "alert")
            alert = parAlert.text
            if alert:
                print(alert)
            else:
                print("Signed in successfully.")
                self.states["sign in"] = True
        except:
            print("Signed in successfully.")
            self.states["sign in"] = True

    def close(self) -> NoReturn:
        self.browser.quit()

    @_checkStates(1)
    def enterDB(self, label: str):
        DBdict = {
            "NGA West2": 1,
            "NGA east": 2
        }
        self.browser.get(
            f"https://ngawest2.berkeley.edu/spectras/new?sourceDb_flag={DBdict[label]}"
        )
        self.browser.execute_script("OnSubmit()")

        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.NAME, "search[search_nga_number]"))
        )
        self.states["enter database"] = True

    @_checkStates(2)
    def search(self, settings: dict = None):
        if settings:
            for label in settings:
                elemName = self.__getElemName(label)
                if elemName:
                    inputElem = self.browser.find_element(By.NAME, elemName)
                    inputElem.clear()
                    inputElem.send_keys(settings[label])

        if self.__clickBtnSearch():
            self.states["search records"] = True
            return True
        return False

    @_checkStates(3)
    def download(self, saveDir: str, timeout: int = 30):
        # 点击选择所有记录并下载
        self.browser.execute_script("getSelectedResult(true)")

        # 处理第一个确认弹窗
        try:
            alert = self.browser.switch_to.alert
            alert.accept()
        except:
            pass

        # 处理第二个确认弹窗
        try:
            alert = self.browser.switch_to.alert
            alert.accept()
        except:
            pass

        # 等待下载链接出现（页面会自动生成下载链接）
        zip_link = WebDriverWait(self.browser, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.zip')]"))
        )

        download_url = zip_link.get_attribute("href")
        if not download_url:
            raise Exception("Failed to get download URL")

        # 使用 requests 下载
        save_name = "download.zip"
        save_path = os.path.join(saveDir, save_name)

        response = requests.get(download_url, stream=True, timeout=timeout)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded: {save_path}")

        # 解压
        unZip(save_path, saveDir)

        # 清理临时文件
        for f in os.listdir(saveDir):
            if f.endswith(".zip") or f.endswith(".csv"):
                os.remove(os.path.join(saveDir, f))

        print("Download and extraction completed.")

    def __clickBtnSearch(self) -> bool:
        self.browser.execute_script("OnSubmit()")

        divNotice = WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.ID, "notice"))
        )
        notice = divNotice.text
        print(notice)

        if " NO " in notice or " exceed " in notice:
            return False
        return True

    @staticmethod
    def __getElemName(label: str) -> str or bool:
        nameDict = {
            "RSNs": "search[search_nga_number]",
            "Event Name": "search[search_eq_name]",
            "Station Name": "search[search_station_name]",
            "Fault Type": "search[faultType]",
            "Magnitude": "search[magnitude]",
            "R_JB": "search[rjb]",
            "R_rup": "search[rrup]",
            "Vs30": "search[vs30]",
            "D5-95": "search[duration]",
            "Pulse": "search[pulse]",
            "Max No. Records": "search[output_num]"
        }

        if label in nameDict:
            return nameDict[label]
        print(f"There is no such setting item: {label}")
        return False
