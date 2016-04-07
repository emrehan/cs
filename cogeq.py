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
        ffrom = datetime.strptime(request.args.get('from'), timeFormat)
        to = datetime.strptime(request.args.get('to'), timeFormat)
        if (not city or not ffrom or not to):
            return dumps( {'Error': 'city, from and to must be provided.'} )
        else:
            activity1 = {"id": "123", "name": "Kizilay", "type": "visit", "picture_url": "https://pbs.twimg.com/profile_images/666942007/kizilay_logo545px.png", "description": "Kizilay is a nice place", "place": "", "directions": "", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            activity2 = {"id": "1234", "name": "Kofi", "type": "visit", "picture_url": "http://img.bleacherreport.net/img/slides/photos/002/990/036/kofi-kingston1_crop_north.jpg?w=630&h=420&q=75", "description": "Kofi is a nice place", "place": "", "directions": "", "from": ffrom.strftime(timeFormat), "to": to.strftime(timeFormat)}
            activities = [activity1, activity2];
            travel = { 'city': city, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat), 'activities': activities }
            travel_id = db.travels.insert_one(travel).inserted_id
            return dumps( { 'travel_id': travel_id, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat), 'activities': activities } )
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
