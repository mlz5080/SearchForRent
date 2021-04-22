from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
import time
#import warnings
#warnings.filterwarnings('ignore')
import json
import boto3
import collections
import googlemaps
from decimal import Decimal

def rentals_crawlling():
    t0 = time.perf_counter()
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    page_cnt = 1
    rentals_url = 'https://rentals.ca/montreal'
    print('so far\n')
    with open('rentalsca.txt', 'w') as k:
        while True:
            print(page_cnt)
            if page_cnt==1:
                driver.get(rentals_url)
            else:
                driver.get(rentals_url+'?p='+str(page_cnt))
            wait = WebDriverWait(driver, 10)
            eles = driver.find_elements_by_xpath('//*[@id="app"]/div[1]/div/div[1]/div[2]/div/div[2]/div[1]/div/*')
            for e in eles:
                if e.get_attribute('class') in 'cta-container col-12':
                    continue
                k.write(e.text)
                k.write('\n')
                ee = e.find_element_by_class_name('listing-card').find_element_by_class_name('listing-card__details').find_element_by_class_name('listing-card__description').find_element_by_tag_name('a')
                k.write(str(ee.get_attribute('href')))
                k.write('\n\n')
            next_e = driver.find_element_by_xpath('/html/body/div[1]/div[1]/div/div[1]/div[2]/div/div[3]/div[1]/ul/li[4]')
            if next_e.get_attribute('class')=='pagination__item pagination__item--disabled':
                break
            else:
                page_cnt+=1
    print('\nso good')
    driver.quit()
    t1 = time.perf_counter() - t0
    print("Time elapsed: ",t1)

def db_update():
    gmaps = googlemaps.Client(key='AIzaSyBTSncweae4I3m5rv0EtW_5leTOkCim-Ng')
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("rentals_sub_urls")
    try:
        table.delete()
    except:
        print("Table does not exists")
    time.sleep(10)
    table = dynamodb.create_table(
    TableName='rentals_sub_urls',
    KeySchema=[
        {
            'AttributeName': 'sub_urls',
            'KeyType': 'HASH'
        },
        {
            'AttributeName': 'price',
            'KeyType': 'RANGE'
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'sub_urls',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'price',
            'AttributeType': 'N'
        },
    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 5,
        'WriteCapacityUnits': 5
    }
    )
    data_list=[]
    temp=[]
    address=[]
    urls=[]
    diction={}
    detail=""
    with open("rentalsca.txt") as record:
        for i in record:
            
            if("$" in i):
                if(len(i.replace("$",""))>5):
                    price=(int(i.replace("$","").replace(" ","").split("-",1)[0].replace("\n","")))
                else:
                    price=(int(i.replace("$","").replace("\n","")))
            elif("QC" in i):
                address=(i.replace("\n",""))
            elif("https" in i):
                diction[i.replace("\n","")]={'price':price,'address':address,'details':detail.replace("\n","")}
            else:
                if(len(i)>2):
                    if((not "Details" in i) and not ("1 " in i)):
                        print(i)
                        detail+=i+" "
                else:
                    detail=""
    #print(diction)
    for item in diction:
        print(diction[item]['address'])
        try:
            geocode_result = gmaps.geocode(diction[item]['address'])
            for i in geocode_result:
                if 'geometry' in i:
                    if 'location' in i['geometry']:
                        diction[item]['lat']=Decimal(str(i['geometry']['location']['lat']))
                        diction[item]['lng']=Decimal(str(i['geometry']['location']['lng']))
        except:
            print("HTTP error")
        

    with table.batch_writer() as batch:
        for i in diction:
            try:
                batch.put_item(
                Item={
                'sub_urls': i,
                'price': diction[i]['price'],
                'address': diction[i]['address'],
                'lat': diction[i]['lat'],
                'lng': diction[i]['lng'],
                'detail':diction[i]['details']
                }
                )
            except:
                print(i," will be skipped")

if __name__ == '__main__':
    rentals_crawlling()
    db_update()
