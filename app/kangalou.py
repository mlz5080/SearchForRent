#import requests
#from bs4 import BeautifulSoup
from selenium import webdriver
#from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
import time

#import warnings
#warnings.filterwarnings('ignore')

#import sys
#from PyQt5.QtWidgets import QApplication
#from PyQt5.QtCore import QUrl
#from PyQt5.QtWebEngineWidgets import QWebEnginePage

'''
class Client(QWebPage):
    def __init__(self, url):
        self.app = QApplication(sys.argv)
        QWebPage.__init__(self)
        self.loadFinished.connect(self.on_page_load)
        self.mainFrame().load(QUrl(url))
        self.app.exec_()
    def on_page_load(self):
        self.app.quit()
'''


'''
def kangalou_go(url):
    headers = {}
    headers['User-Agent'] = 'Mozilla/5.0'
    with requests.Session() as s:
        r = s.get(url, headers=headers)
        soup = BeautifulSoup(r.content,"lxml")
        a_tags = soup.find_all('a')
        with open("kresult.json","w") as k:
            for i in a_tags:
                k.write(str(i))
                k.write("\n")
'''
if __name__ == '__main__':
    kangalou_url = 'https://www.kangalou.com/en/location/montreal?q=NZA7DsIwEAVPQ2rvrj9xkQZxERRRUICQggTHJ3heKmtk777xW0%2FlnE7lslhOaVp3sj9Fnwc40AfEeBelDMpQ80HlT8eKCtiABrQBM0M1D%2BpcAZYgtptpfYDOZYVk0jQpldBoUQjWVqXNj6yBHTuTUcHPpKTfH83w1uVUiHVXDrEejJLqWaPU43IKLZZT5XdOR6YYKWXK9C5hDIOajL1hEHtCRqGnGBm6kSFsQ0KNRuMQIjMkpMtDCL%2BgIyMkJ%2BnN0%2Btxfy5pP67f%2FdiW5%2B1z294%2F'

    #t0 = time.perf_counter()
    op = Options()
    op.headless = True
    #driver = webdriver.Firefox(options = op)
    driver = webdriver.Chrome(options = op)
    print('so far')
    driver.get(kangalou_url)
    wait = WebDriverWait(driver, 10)
    ele = driver.find_element_by_xpath('//*[@id="js-GenResult"]')
    print(ele)
    #html = driver.execute_script('return document.documentElement.outerHTML')                                                                                           
    #html = driver.page_source 
    driver.quit()
    #t1 = time.perf_counter() - t0
    #print(t1)

    '''
    client_response = Client(url)
    source = client_response.mainFrame().toHtml()
    soup = BeautifulSoup(source,"lxml")
    a_tags = soup.find_all('div', id='slist')
    with open("kresult.txt","w") as k:
        for i in a_tags:
            k.write(str(i))
            k.write("\n")
    '''
    #kangalou_go(kangalou_url)
    #print(*myurl, sep = "\n")
    #print(len(myurl))
