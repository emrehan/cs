from datetime import datetime
from bson import Binary, Code
from bson.json_util import dumps
from flask import Flask, request, jsonify
from flask.ext.mongoengine import MongoEngine
from mongoengine import *

import json
import os
import requests 
import uuid

class Travel(DynamicDocument):
    travel_id = StringField()

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'cogeq',
    'host': 'mongodb://u:p@ds013270.mlab.com:13270/cogeq'
}
db = MongoEngine(app)    

config = json.load(open('config.json'))

@app.route("/", methods=['GET'])
def hello():
    return "COGEQ!"

@app.route("/db", methods=['GET', 'POST', 'DELETE'])
def dummy_db():
    if request.method == 'GET':
        return dumps( {'travels': Travel.objects()} )
    if request.method == 'POST':
        travel = Travel(travel_id = str(uuid.uuid1()))
        travel.save()
        return dumps( {'travel': travel} )

@app.route("/login", methods=["GET"])
def login():
    code = request.args.get("code")
    client_id = "XWWK4XOYWX3J1XDRN43LL2V0EB41OFCDF3EBZ1CZIABKA1DL"
    client_secret = "MGDCFYKO2SZP0TNPWOI4KJ2P5GVHRTWUIAB4O0I25PBH2BAS"
    
    if code:
        r = requests.get("https://foursquare.com/oauth2/access_token?client_id=" + client_id + "&client_secret=" + client_secret + "&grant_type=authorization_code&code=" + code)
        if (r.status_code == 200):
            return dumps(r.json())
        else:
            return dumps({"Error": "Could not login to foursquare."})
        
@app.route("/cities", methods=['GET'])
def search_cities():
    query = request.args.get('query')

    if query:
        r = requests.get('https://maps.googleapis.com/maps/api/place/autocomplete/json?types=(cities)&key=' + config['keys']['google_places'] + '&input=' + query )        
        if (r.status_code == 200):     
            cities = list( map( lambda x: x['description'], r.json()['predictions'] ) )
            return dumps( {'cities': cities}, ensure_ascii=False )
        else:
            return dumps( {'Error': 'Error while getting Google Place API response'}, ensure_ascii=False )
    else:
        default_cities = ['Istanbul, Turkey', 'London, United Kingdom', 'Izmir, Turkey', 'Singapore, Singapore', 'NYC, United States']
        return dumps( {'cities': default_cities}, ensure_ascii=False)
        
@app.route("/travels", methods=['POST'])
def create_travel():
    timeFormat = "%Y-%m-%dT%H:%M:%S";
    try:
        city = request.args.get('city')
        access_token = request.args.get('access_token')
        ffrom = datetime.strptime(request.args.get('from'), timeFormat)
        to = datetime.strptime(request.args.get('to'), timeFormat)
        if (not city or not access_token or not ffrom or not to):
            return dumps( {'Error': 'city, from and to must be provided.'} )
        else:
            r = requests.get("https://api.foursquare.com/v2/users/self/checkins?oauth_token=" + access_token + "&limit=250&offset=0&v=20160417")
            place1 = {"latitude": "39.9208289", "longitude": "32.85387930000002"}
            activity1 = {"id": "123", "name": "Kizilay", "type": "visit", "place": place1, "picture_url": "https://upload.wikimedia.org/wikipedia/commons/b/b3/K%C4%B1z%C4%B1lay_Square_in_Ankara,_Turkey.JPG", "description": "Kizilay is a nice place", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            place2 = {"latitude": "39.1667", "longitude": "35.6667"}
            activity2 = {"id": "1234", "name": "Ankara Kalesi", "type": "visit", "place": place2, "picture_url": "http://gezipgordum.com/wp-content/uploads/Ankara-Kalesi2.jpg", "description": "Kofi is a nice place", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            place3 = {"latitude": "39.9208289", "longitude": "32.85387930000002"}
            activity3 = {"id": "123", "name": "Kizilay", "type": "visit", "place": place1, "picture_url": "https://upload.wikimedia.org/wikipedia/commons/b/b3/K%C4%B1z%C4%B1lay_Square_in_Ankara,_Turkey.JPG", "description": "Kizilay is a nice place", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            place4 = {"latitude": "39.1667", "longitude": "35.6667"}
            activity4 = {"id": "1234", "name": "Ankara Kalesi", "type": "visit", "place": place2, "picture_url": "http://gezipgordum.com/wp-content/uploads/Ankara-Kalesi2.jpg", "description": "Kofi is a nice place", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            place5 = {"latitude": "39.9208289", "longitude": "32.85387930000002"}
            activity5 = {"id": "123", "name": "Kizilay", "type": "visit", "place": place1, "picture_url": "https://upload.wikimedia.org/wikipedia/commons/b/b3/K%C4%B1z%C4%B1lay_Square_in_Ankara,_Turkey.JPG", "description": "Kizilay is a nice place", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            place6 = {"latitude": "39.1667", "longitude": "35.6667"}
            activity6 = {"id": "1234", "name": "Ankara Kalesi", "type": "visit", "place": place2, "picture_url": "http://gezipgordum.com/wp-content/uploads/Ankara-Kalesi2.jpg", "description": "Kofi is a nice place", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            activities = [activity1, activity2, activity3, activity4, activity5, activity6];
            travel = { 'city': city, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat), 'activities': activities}
            travel_id = Travel(travel_id = str(uuid.uuid1()))
            travel.save()
            return dumps( { 'travel_id': travel_id, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat), 'activities': activities, "response": r.json()} )
    except:
        return dumps({'Error': 'Error occured'})

@app.route("/travels/<travel_id>", methods=['GET', 'PUT'])
def travel(travel_id):
    if request.method == 'GET':
        return dumps( {'travels': list( db.travels.find({"_id": bson.ObjectId(oid=str(travel_id))}) )} )
    if request.method == 'PUT':
        timeFormat = "%Y-%m-%dT%H:%M:%S";
        city = request.args.get('city')
        ffrom = datetime.strptime(request.args.get('from'), timeFormat)
        to = datetime.strptime(request.args.get('to'), timeFormat)
        db.travels.update_one({"_id": bson.ObjectId(oid=str(travel_id))}, {"$set": {"city": city, "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat) }})
        return dumps( { 'travel_id': travel_id, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat) } )

if __name__ == "__main__":
    app.debug = True 
    port = int(os.environ.get("PORT", 5000))   
    app.run(port=port)
