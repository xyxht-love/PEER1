import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from IO import unZip


class PeerNGA:

    def __init__(self, driverPath=None):

        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")
        options.add_argument("--disable-blink-features=AutomationControlled")

        service = Service(driverPath) if driverPath else Service()

        self.browser = webdriver.Chrome(service=service, options=options)

        self.wait = WebDriverWait(self.browser, 20)

    # =========================
    # 1. 登录
    # =========================
    def signIn(self, email, password):

        self.browser.get(
            "https://ngawest2.berkeley.edu/users/sign_in"
        )

        self.wait.until(
            EC.presence_of_element_located((By.NAME, "user[email]"))
        ).send_keys(email)

        self.browser.find_element(By.NAME, "user[password]").send_keys(password)

        self.browser.find_element(By.NAME, "commit").click()

        time.sleep(2)

        print("✅ Signed in")

    # =========================
    # 2. 进入数据库
    # =========================
    def enterDB(self, label):

        db_map = {
            "NGA West2": 1,
            "NGA East": 2
        }

        url = f"https://ngawest2.berkeley.edu/spectras/new?sourceDb_flag={db_map[label]}"

        self.browser.get(url)

        self.wait.until(
            EC.presence_of_element_located((By.NAME, "search[search_nga_number]"))
        )

        print("✅ Entered DB")

    # =========================
    # 3. 搜索
    # =========================
    def search(self, settings=None):

        if settings:
            for k, v in settings.items():

                name_map = {
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

                if k in name_map:
                    elem = self.browser.find_element(By.NAME, name_map[k])
                    elem.clear()
                    elem.send_keys(str(v))

        # 点击搜索
        self.browser.execute_script("OnSubmit()")

        time.sleep(2)

        notice = self.browser.find_element(By.ID, "notice").text
        print("Search:", notice)

        return "NO" not in notice and "exceed" not in notice

    # =========================
    # 4. 下载（核心升级）
    # =========================
    def download(self, saveDir):

        os.makedirs(saveDir, exist_ok=True)

        # 点击 download
        self.browser.execute_script("getSelectedResult(true)")

        time.sleep(3)

        # =========================
        # ⭐ 核心：从页面抓 ZIP URL
        # =========================
        links = self.browser.find_elements(By.TAG_NAME, "a")

        zip_url = None
        for a in links:
            href = a.get_attribute("href")
            if href and ".zip" in href:
                zip_url = href
                break

        if not zip_url:
            raise Exception("❌ Cannot find ZIP download link")

        print("📦 Download URL:", zip_url)

        # =========================
        # requests 下载
        # =========================
        cookies = self.browser.get_cookies()
        session = requests.Session()

        for c in cookies:
            session.cookies.set(c["name"], c["value"])

        r = session.get(zip_url, stream=True)

        zip_path = os.path.join(saveDir, "peer.zip")

        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

        # 解压
        unZip(zip_path, saveDir)

        os.remove(zip_path)

        print("✅ Download & unzip finished")

    # =========================
    # 5. 关闭
    # =========================
    def close(self):
        self.browser.quit()
