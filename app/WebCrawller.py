import requests
from bs4 import BeautifulSoup
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed
import json
from lxml.html import fromstring
import traceback
import time
from timeit import default_timer as timer
import gc
import re
import boto3
from boto3.dynamodb.conditions import Key
import googlemaps
from decimal import Decimal

gmaps = googlemaps.Client(key='')

kijiji_quebec = "/h-quebec/9001"
kijiji_grand_montreal = "/h-grand-montreal/80002"
kijiji_foreign_url = "https://www.kijiji.ca/h-ville-de-montreal/1700281/"
kijiji_url = "https://www.kijiji.ca"
english = "?siteLocale=en_CA"
myurl = "https://www.kijiji.ca/b-a-louer/ville-de-montreal/c30349001l1700281"
headers = {}
headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36'
thread_list=[]
nextpage=myurl
URLS=[]
kijiji_data={}
dynamodb = boto3.resource('dynamodb')
table_kijiji = dynamodb.Table("kijiji_sub_urls")
table_guiker = dynamodb.Table("guiker_sub_urls")


def kijiji_look_for_rent_outer_loop():
    global nextpage
    global dynamodb
    global table_kijiji
    while(nextpage!=None):
        kijiji_look_for_rent()
    try:
        table_kijiji.delete()
    except:
        print("Table does not exists")
    time.sleep(10)
    table_kijiji=dynamodb.create_table(TableName='kijiji_sub_urls',KeySchema=[
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

    update_kijiji()

def kijiji_find_foreign_url():
    url=kijiji_url+kijiji_quebec
    requests.get(url)
    url = kijiji_url+kijiji_grand_montreal+english
    body=requests.get(url)

def kijiji_look_for_rent():
    global URLS
    global nextpage
    global kijiji_data
    kijiji_find_foreign_url()
    suburl_list=[]
    local=[]
    found=True
    flag= True
    entered=False
    nbofr=0
    with FuturesSession(max_workers=8,session=requests.Session()) as rq_session:
        while(found):
            found=False;
            response = rq_session.get(nextpage+english)
            mycontent = response.result().content
            soup = BeautifulSoup(mycontent,"lxml")
            a_link_tags = soup.find_all("a",href=True,class_="title")
            a_next=soup.find("a",href=True,title="Next") if soup.find("a",href=True,title="Suivante")==None else soup.find("a",href=True,title="Suivante")
            found = True if a_next!=None else False
            nextpage= kijiji_url+a_next.get('href') if a_next != None else None
            print(len(a_link_tags))
            for link in a_link_tags:
                URLS.append(link.get('href'))
                suburl_list.append(kijiji_url+link.get('href'))
                local.append(link.get('href'))

            list_thread=[]
            list_response=[]
            for i in suburl_list:
                list_thread.append(rq_session.get(i,verify=True))

            for index,job in enumerate(as_completed(list_thread)):
                list_response.append(job.result())
            list_thread=[]
            gc.collect()
            save = {}
            for index in range(len(list_response)):
                newsoup = BeautifulSoup(list_response[index].content,"lxml")
                span_price = newsoup.find("span",class_="currentPrice-2842943473")
                span_address =newsoup.find("span",itemprop="address")
                price = span_price.string.string if ((span_price != None) and (span_price.string != None) and (span_price.string.string!=None)) else 4000
                address = span_address.string if span_address!= None else ""
                price = price.replace(".00","").replace("$","").replace(",","")
                price = ''.join(x for x in price if x.isdigit())
                if(len(price)>0):
                    price=int(price)
                else:
                    price=4000;
                save[list_response[index].url]={'price':price,'address':address}

            if(entered):
                with open("data.txt","a") as file:
                    json.dump(save,file)
                    file.write("\n")
                del save
            else:
                with open("data.txt","w") as file:
                    json.dump(save,file)
                    file.write("\n")
                del save
                entered=True
            suburl_list=[]
            URLS = list(dict.fromkeys(URLS))
    return

def update_kijiji():
    global table_kijiji
    with open("data.txt") as file:
        with table_kijiji.batch_writer() as batch:
            for line in file:
                data = json.loads(line)
                for j in data:
                    geocode_result = gmaps.geocode(data[j]['address'])
                    for i in geocode_result:
                        if 'geometry' in i:
                            if 'location' in i['geometry']:
                                data[j]['lat']=Decimal(str(i['geometry']['location']['lat']))
                                data[j]['lng']=Decimal(str(i['geometry']['location']['lng']))
                    try:
                        batch.put_item(
                        Item={
                                'sub_urls': j,
                                'price': data[j]['price'],
                                'address': data[j]['address'],
                                'lat':data[j]['lat'],
                                'lng':data[j]['lng'],
                        },
                        )
                    except:
                        print("item exists")

def guiker_look_for_rent():
    global table_guiker
    try:
        table_guiker.delete()
    except:
        print("Table does not exists")
    time.sleep(10)
    table_guiker = dynamodb.create_table(
    TableName='guiker_sub_urls',
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
    Headers ={'Host':'server.guiker.com','Connection':'keep-alive',
    'Pragma':'no-cache','Cache-Control': 'no-cache',
    'Access-Control-Request-Method': 'POST',
    'Origin': 'https://guiker.com','User-Agent':'Mozilla/5.0',
    'Access-Control-Request-Headers': 'content-type',
    'Accept': '*/*','Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://guiker.com/en/listings?lowPrice=0&highPrice=4000&moveInDate=2019-11-24&longitude=-73.567256&latitude=45.5016889&radius=0.002229909329209079&zoom=15',
    'Accept-Encoding': 'gzip, deflate, br','Accept-Language': 'zh-CN,zh;q=0.9,en-GB;q=0.8,en-US;q=0.7,en;q=0.6'
    }

    payload={"cityId":1,"lowPrice":0,"highPrice":4000,"currency":"CAD",
    "moveInDate":"2019-11-24","bedroomCount":'',"page":0,"perPage":100,
    "shiftDayBackward":60,"shiftDayForward":365,"longitude":-73.567256,
    "latitude":45.5016889,"radius":2,"zoom":15}

    postheader = {'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language':'zh-CN,zh;q=0.9,en-GB;q=0.8,en-US;q=0.7,en;q=0.6',
    'Cache-Control': 'no-cache','Connection': 'keep-alive',
    'Content-Length': '256','Content-Type': 'application/json;charset=UTF-8',
    'Host': 'server.guiker.com','Origin': 'https://guiker.com',
    'Pragma': 'no-cache',
    'Referer':'https://guiker.com/en/listings?lowPrice=0&highPrice=4000&moveInDate=2019-11-24&bcount=&longitude=-73.567256&latitude=45.5016889&radius=0.002229909329209079&zoom=15',
    'Sec-Fetch-Mode': 'cors','Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0'}

    origin_url = "https://guiker.com/en/"
    data_url=origin_url+"listings/"
    get_site_map = ["https://server.guiker.com/api/amenities?language=en",
    "https://server.guiker.com/api/cities/1/references",
    "https://api.mapbox.com/styles/v1/guiker/ciwf1z53c002n2qof6z8a6ara/tiles/256/15/9687/11722?access_token=pk.eyJ1IjoiZ3Vpa2VyIiwiYSI6ImNpaHhuaG82ODAzYml0c2toNHViamI3bjQifQ.-YtAv_4OV8WzHXdUQyekIQ"
    ]
    option_post_site_map = "https://server.guiker.com/api/listings/search"
    requests.get(origin_url)
    for i in get_site_map:
        requests.get(i)
    requests.options(url=option_post_site_map,headers=Headers)
    #response = requests.post(url=option_post_site_map,headers=postheader,json=payload)
    #print(response.content)
    payload1={"cityId":1,"lowPrice":0,"highPrice":4000,"currency":"CAD",
    "moveInDate":"2019-11-24","bedroomCount":'',"page":0,"perPage":100,
    "shiftDayBackward":60,"shiftDayForward":365,"longitude":-73.567256,
    "latitude":45.5016889,"radius":2,"zoom":15}
    content = requests.post(url=option_post_site_map,headers=postheader,json=payload1).content
    content = json.loads(content.decode())
    data = content['data']
    price=[]
    guiker_data={}
    for i in data:
        print(i)
        address=i['streetNumber']+" "+i['streetName']+", "+i['zipcode']
        guiker_data[data_url+str(i['id'])]={'price':int(i['lowestPrice']),'address':address}

    for item in guiker_data:
        geocode_result = gmaps.geocode(guiker_data[item]['address'])
        for i in geocode_result:
            if 'geometry' in i:
                if 'location' in i['geometry']:
                    guiker_data[item]['lat']=Decimal(str(i['geometry']['location']['lat']))
                    guiker_data[item]['lng']=Decimal(str(i['geometry']['location']['lng']))

    with table_guiker.batch_writer() as batch:
        for i in guiker_data:
            batch.put_item(
            Item={
                    'sub_urls': i,
                    'price': guiker_data[i]['price'],
                    'address': guiker_data[i]['address'],
                    'lat':guiker_data[i]['lat'],
                    'lng':guiker_data[i]['lng'],
            },
            )
    return

def kijiji_db_update():
    global table_kijiji
    cache_url = []
    list_thread=[]
    list_response=[]
    kijiji_db=table_kijiji.scan()['Items']
    with FuturesSession(max_workers=8,session=requests.Session()) as rq_session:
        for i in kijiji_db:
            cache_url.append(i['sub_urls']+english)
        for i in cache_url:
            list_thread.append(rq_session.get(i,verify=True))
            cache_url=[]
            gc.collect()
        for index,job in enumerate(as_completed(list_thread)):
            list_response.append(job.result())
        list_thread=[]
        gc.collect()

    for i in list_response:
        soup = BeautifulSoup(i.content,'lxml')
        h3 = soup.find("h3",string=re.compile("No Longer Available"))
        if(h3!=None):
            response = table_kijiji.query(KeyConditionExpression=Key('sub_urls').eq(i.url.split("?")[0]))
            response['Items'][0].pop('address', None)
            key = response['Items'][0]
            print(key)
            table_kijiji.delete_item(Key=key)
    return

if __name__ == '__main__':
    print("Main")
    guiker_look_for_rent()
    #gc.collect()
    #kijiji_look_for_rent()
    #kijiji_db_update()
    #kijiji_look_for_rent_outer_loop()




