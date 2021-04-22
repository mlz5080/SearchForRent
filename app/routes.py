from flask import Flask,request
import threading
import requests
import os
from bs4 import BeautifulSoup
from flask import render_template
import boto3
from boto3.dynamodb.conditions import Key, Attr
import googlemaps
from flask_restful import Resource, Api
from WebCrawller import guiker_look_for_rent
from WebCrawller import kijiji_look_for_rent_outer_loop
from rentals_script import rentals_crawlling
from rentals_script import db_update
from flask_httpauth import HTTPBasicAuth
from flask import g,jsonify
import math
auth = HTTPBasicAuth()

app = Flask(__name__)
api = Api(app)
import time

gmaps = googlemaps.Client(key='')
dynamodb = boto3.resource('dynamodb')
kijiji_table = dynamodb.Table('kijiji_sub_urls')
guiker_table = dynamodb.Table('guiker_sub_urls')
rentalsca_table = dynamodb.Table('rentals_sub_urls')
user_table = dynamodb.Table('users')



#-----------------------REST API DESIGN-----------------------#
@app.route('/api/')
@auth.login_required
def get_resource():
    return "Success!"

#-----------------------REST API DESIGN-----------------------#
#-----------------------REST API GET--------------------------#
@app.route('/api/<db>/',methods=['GET'])
@auth.login_required
def get_list(db):
	if("kijiji" in db):
		try:
			local_copy=kijiji_table.scan()['Items']
		except:
			return "Error! Kijiji Table got deleted"
	elif("guiker" in db):
		try:
			local_copy=guiker_table.scan()['Items']
		except:
			return "Error! Guiker Table got deleted"
	elif("rentals" in db):
		try:
			local_copy=rentalsca_table.scan()['Items']
		except:
			return "Error! Rentals Table got deleted"
	else:
		abort(404, message="Wrong format!")
	for i in local_copy:
		i['price'] = int(i['price'])
		i['lat'] = float(i['lat'])
		i['lng'] = float(i['lng'])
	return jsonify(local_copy)

@app.route('/api/<db>/<url>',methods=['GET'])
@auth.login_required
def get_url(db,url):
	if("kijiji" in db):
		try:
			local_copy=kijiji_table.scan()['Items']
		except:
			return "Error! Kijiji Table got deleted"
		local_table=kijiji_table
	elif("guiker" in db):
		try:
			local_copy=guiker_table.scan()['Items']
		except:
			return "Error! Guiker Table got deleted"
		local_table=guiker_table
	elif("rentals" in db):
		try:
			local_copy=rentalsca_table.scan()['Items']
		except:
			return "Error! Guiker Table got deleted"
		local_table=rentalsca_table
	else:
		abort(404, message="Wrong format!")
	for i in local_copy:
		if(url in i['sub_urls']):
			response = local_table.query(KeyConditionExpression=Key('sub_urls').eq(i['sub_urls']))
			apiresponse = response['Items'][0]
			apiresponse['price'] = int(apiresponse['price'])
			apiresponse['lat'] = float(apiresponse['lat'])
			apiresponse['lng'] = float(apiresponse['lng'])
			return apiresponse
	return "Item not found!"

#-----------------------REST API DESIGN-----------------------#
#-----------------------REST API POST--------------------------#
@app.route('/api/<db>/',methods=['POST'])
@auth.login_required
def post_list(db):
	if("kijiji" in db):
		mythread=threading.Thread(target=kijiji_look_for_rent_outer_loop)
		mythread.start()
	elif("guiker" in db):
		guiker_look_for_rent()
	elif("rentals" in db):
		rentals_crawlling()
		db_update()
	else:
		abort(404, message="Wrong format!")
	mythread.join()
	return db+" DataBase updated!"

@app.route('/api/user/<parameter>',methods=['POST'])
@auth.login_required
def post_user(parameter):
	if("username" in parameter and "password" in parameter):
		string = parameter.split("&")
		username=string[0].replace("?","")
		password=string[1]
		username=username.split("=")[1]
		password=password.split("=")[1]
		if(len(username)!=0 and len(password)!=0):
			user_table.put_item(
				Item={
				'login':username,
				'password':password,
				}
			)
			return "New user information updated!"
		else:
			abort(404, message="Invalid input!")
	else:
		abort(404, message="Invalid input!")

#-----------------------REST API DESIGN-----------------------#
#-----------------------REST API DELETE--------------------------#
@app.route('/api/<db>/',methods=["DELETE"])
@auth.login_required
def del_list(db):
	if("kijiji" in db):
		kijiji_table.delete()
	elif("guiker" in db):
		guiker_table.delete()
	elif("rentals" in db):
		rentalsca_table.delete()
	else:
		abort(404, message="Wrong format!")
	return db+ " DataBase deleted!"

@app.route('/api/<db>/<url>',methods=["DELETE"])
@auth.login_required
def del_url(db,url):
	if("kijiji" in db):
		try:
			local_copy=kijiji_table.scan()['Items']
		except:
			return "Error! Kijiji Table got deleted before"
		local_table=kijiji_table
	elif("guiker" in db):
		try:
			local_copy=guiker_table.scan()['Items']
		except:
			return "Error! Guiker Table got deleted before"
		local_table=guiker_table
	elif("rentals" in db):
		try:
			local_copy=rentalsca_table.scan()['Items']
		except:
			return "Error! Rentals Table got deleted before"
		local_table=rentalsca_table
	else:
		abort(404, message="Wrong format!")
	for i in local_copy:
		if(url in i['sub_urls']):
			response = local_table.query(KeyConditionExpression=Key('sub_urls').eq(i['sub_urls']))
			apiresponse.pop('price',None)
			apiresponse.pop('lat',None)
			apiresponse.pop('lng',None)
			return rentalsca_table.delete_item(Key=apiresponse)
		return "Item not found!"

#-----------------------Web Service DESIGN-------------------------------#
@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/Data',methods=['GET'])
def getdata():
	cache={}
	lowp=int(request.args.get('lowprice')) if len(request.args.get('lowprice'))>0  else 300
	highp=int(request.args.get('highprice')) if len(request.args.get('highprice'))>0 else 5000
	lowp = 300 if lowp<300 or lowp>4000 else lowp
	highp = 4000 if (highp>5000 or highp<0) else highp
	response_kijiji = kijiji_table.scan(
    FilterExpression=Attr('price').lt(highp) & Attr('price').gt(lowp)
	)
	response_guiker = guiker_table.scan(
    FilterExpression=Attr('price').lt(highp) & Attr('price').gt(lowp)
	)
	response_rentalsca = rentalsca_table.scan(
    FilterExpression=Attr('price').lt(highp) & Attr('price').gt(lowp)
	)
	#t1 = time.perf_counter()
	response_all = response_rentalsca['Items']+response_guiker['Items']+response_kijiji['Items']
	return render_template("result.html",result = response_all)

@app.route('/DataAnalysis',methods=['GET'])
def get_analysis():
	lowp = 300
	highp = 5000
	price=[]
	response = []
	response.append("Before Filtering the data")
	response_kijiji = kijiji_table.scan()
	response_guiker = guiker_table.scan()
	response_rentalsca = rentalsca_table.scan()
	response_all = response_rentalsca['Items']+response_guiker['Items']+response_kijiji['Items']
	for i in response_all:
		price.append(i['price'])
	price.sort()
	print(len(price))

	five_percentile = price[math.ceil((len(price)-1)*0.05)]
	ten_percentile = price[math.ceil((len(price)-1)*0.1)]
	twenty_five_percentile = price[math.ceil((len(price)-1)*0.25)]
	fifty_percentile = price[math.ceil((len(price)-1)*0.5)]
	seventy_five_percentile = price[math.ceil((len(price)-1)*0.75)]
	ninety_percentile = price[math.ceil((len(price)-1)*0.9)]
	ninety_five_percentile = price[math.ceil((len(price)-1)*0.95)]
	response.append("Max price -> "+ str(price[len(price)-1])) 
	response.append("Median price -> " + str(price[int(len(price)/2)]))
	response.append("Min price -> " + str(price[0]))
	response.append("5 percentile -> "+str(five_percentile))
	response.append("10 percentile -> "+str(ten_percentile))
	response.append("25 percentile -> "+str(twenty_five_percentile))
	response.append("50 percentile -> "+str(fifty_percentile))
	response.append("75 percentile -> "+str(seventy_five_percentile))
	response.append("90 percentile -> "+str(ninety_percentile))
	response.append("95 percentile -> "+str(ninety_five_percentile))

	response_kijiji = kijiji_table.scan(
    FilterExpression=Attr('price').lt(highp) & Attr('price').gt(lowp)
	)
	response_guiker = guiker_table.scan(
    FilterExpression=Attr('price').lt(highp) & Attr('price').gt(lowp)
	)
	response_rentalsca = rentalsca_table.scan(
    FilterExpression=Attr('price').lt(highp) & Attr('price').gt(lowp)
	)
	response_all = response_rentalsca['Items']+response_guiker['Items']+response_kijiji['Items']
	price = []
	for i in response_all:
		price.append(i['price'])
	price.sort()
	print(len(price))
	five_percentile = price[math.ceil((len(price)-1)*0.05)]
	ten_percentile = price[math.ceil((len(price)-1)*0.1)]
	twenty_five_percentile = price[math.ceil((len(price)-1)*0.25)]
	fifty_percentile = price[math.ceil((len(price)-1)*0.5)]
	seventy_five_percentile = price[math.ceil((len(price)-1)*0.75)]
	ninety_percentile = price[math.ceil((len(price)-1)*0.9)]
	ninety_five_percentile = price[math.ceil((len(price)-1)*0.95)]

	response.append("After Filtering the data (lowest price=300) (highest price = 5000)") 
	response.append("Max price -> "+ str(price[len(price)-1]))
	response.append("Median price -> " + str(price[int(len(price)/2)]))
	response.append("Min price -> " + str(price[0]))
	response.append("5 percentile -> "+str(five_percentile))
	response.append("10 percentile -> "+str(ten_percentile))
	response.append("25 percentile -> "+str(twenty_five_percentile))
	response.append("50 percentile -> "+str(fifty_percentile))
	response.append("75 percentile -> "+str(seventy_five_percentile))
	response.append("90 percentile -> "+str(ninety_percentile))
	response.append("95 percentile -> "+str(ninety_five_percentile))
	return render_template("dataanalysis.html",result = response)

@auth.verify_password
def verify_password(username, password):
	print(username)
	print(password)
	if(len(username)==0 or len(password)==0):
		return False
	print("entered here")
	print(username,password)
	response = user_table.query(KeyConditionExpression=Key('login').eq(username))
	print(response)
	if len(response['Items'])==0 or not response['Items'][0]['password'] in password:
		return False
	#g.user = user
	return True

def DB_hourly_update_guiker():
	while(True):
		time.sleep(3600)
		guiker_look_for_rent()
def DB_hourly_update_kijiji():
	while(True):
		time.sleep(7200)
		kijiji_look_for_rent_outer_loop()
def DB_hourly_update_rentals():
	while(True):
		time.sleep(3600)
		rentals_crawlling()
		db_update()

if __name__ == '__main__':
	threads = []
	#threads.append(threading.Thread(target=DB_hourly_update_guiker).start())
	#threads.append(threading.Thread(target=DB_hourly_update_kijiji).start())
	#threads.append(threading.Thread(target=DB_hourly_update_rentals).start())
	app.debug = True
	app.run(host='0.0.0.0',port=80)
	#for i in threads:
		#i.join()
