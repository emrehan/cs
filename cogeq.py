from datetime import datetime
from bson import Binary, Code
from bson.json_util import dumps
from flask import Flask, request, jsonify
from flask.ext.mongoengine import MongoEngine
from mongoengine import *
from scipy import spatial

import numpy
import operator
import json
import os
import requests 
import uuid

class Travel(DynamicDocument):
    travel_id = StringField()
    
class Place:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
class Activity:
    def __init__(self, id, name, description, picture_url, place):
        self.id = id
        self.name = name
        self.description = description
        self.picture_url = picture_url
        self.place = place
    def addFromTo(self, ffrom, to):
        self.ffrom = ffrom
        self.to = to

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
            categories = []
            checkinCounts = []
            with open("categories.txt", "r") as f:
                lines = f.readlines()
                for line in lines:
                    categories.append(line)
                    checkinCounts.append(0)
            data = json.loads(r.text)
            for item in data["response"]["checkins"]["items"]:
                if item["venue"]["categories"][0]["name"] in categories:
                    categoryIndex = categories.index(item["venue"]["categories"][0]["name"])
                    checkinCounts[categoryIndex] += 1

            '''place1 = {"latitude": "39.9208289", "longitude": "32.85387930000002"}
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
            activities = [activity1, activity2, activity3, activity4, activity5, activity6];'''
            return dumps("asd2")

            #BURAYA EKLİYORUM
            prePath = "checkins/"
            cityName = "London/"
            expertListFileName = "experts"
            fileSuffix = ".csv"
            delimiter = ","

            expertsFilePath = prePath + cityName + expertListFileName + fileSuffix
            expertCheckinsPrefix = prePath + cityName


            #Turkish Restaurant,Restaurant,Museum

            #TODO Find category-checkin count vector of the user
            userCategoryCheckinCounts = checkinCounts

            #Iterate through experts
            expertsFile = open(expertsFilePath, "r")
            lines = expertsFile.readlines()
            cosineSimilarities = {}

            for line in lines:
                tokens = line.split(delimiter)
                expertCategoryCheckinCounts = tokens[1:]
                expertCategoryCheckinCounts = [int(numeric_string) for numeric_string in expertCategoryCheckinCounts]
                cosineSimilarity = 1 - spatial.distance.cosine(userCategoryCheckinCounts, expertCategoryCheckinCounts)
                cosineSimilarities[tokens[0]] = cosineSimilarity
            estimatedRankings = {}
            #Find estimated rankings
            for expert, similarity in cosineSimilarities.items():
                expertCheckinsPath = expertCheckinsPrefix + expert + fileSuffix
                checkinsFile = open(expertCheckinsPath, "r")
                lines = checkinsFile.readlines()

                for line in lines:
                    tokens = line.split(delimiter)
                    venueId = tokens[0]
                    venueCheckinCount = float(tokens[1])
                    estimatedRanking = cosineSimilarities[expert] * venueCheckinCount

                    #TODO Need decision?
                    if venueId in estimatedRankings:
                        estimatedRankings[venueId] = max(estimatedRankings[venueId], estimatedRanking)
                    else:
                        estimatedRankings[venueId] = estimatedRanking

            sortedEstimatedRankings = sorted(estimatedRankings.items(), key=operator.itemgetter(1))
            sortedEstimatedRankings.reverse()

            #print(sortedEstimatedRankings)
            activities = []
            for venueId, ranking in sortedEstimatedRankings[:3]:
                photoResponse = requests.get("https://api.foursquare.com/v2/venues/" + venueId + "/photos?oauth_token=" + access_token + "&v=20160417")
                photoItem = photoResponse["response"]["photos"]["items"][0]
                prefix = photoItem["prefix"]
                suffix = photoItem["suffix"]
                photoURL = prefix + "500x300" + suffix
                
                venueResponse = requests.get("https://api.foursquare.com/v2/venues/" + venueId + "?oauth_token=" + access_token + "&v=20160417")
                venue = venueResponse["response"]["venue"]
                place = Place(venue["location"]["lat"], venue["location"]["lng"])
                activity = Activity(venueId, venue["name"], "Kofi is a nice place!", photoURL, place)
                activity.addFromTo(ffrom.strftime(timeFormat), to.strftime(timeFormat))
                activities.append(activity)
            # BURAYA EKLEDİM BİTTİ

            travel = { 'city': city, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat), 'activities': activities}
            return dumps( { 'travel_id': 3, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat), 'activities': activities })
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

@app.route("/travels/<travel_id>/<activity_id>", methods=['DELETE'])
def delete_travel(travel_id, activity_id):
    try:
        place2 = {"latitude": "39.1667", "longitude": "35.6667"}
        activity2 = {"id": "1234", "name": "Ankara Kalesi", "type": "visit", "place": place2, "picture_url": "http://gezipgordum.com/wp-content/uploads/Ankara-Kalesi2.jpg", "description": "Kofi is a nice place", "from": "2016-04-04T20:00:00", "to": "2016-04-04T20:00:00"}
        place3 = {"latitude": "39.9208289", "longitude": "32.85387930000002"}
        activity3 = {"id": "123", "name": "Kizilay", "type": "visit", "place": place3, "picture_url": "https://upload.wikimedia.org/wikipedia/commons/b/b3/K%C4%B1z%C4%B1lay_Square_in_Ankara,_Turkey.JPG", "description": "Kizilay is a nice place", "from": "2016-04-04T20:00:00", "to": "2016-04-04T20:00:00"}
        place4 = {"latitude": "39.1667", "longitude": "35.6667"}
        activity4 = {"id": "1234", "name": "Ankara Kalesi", "type": "visit", "place": place4, "picture_url": "http://gezipgordum.com/wp-content/uploads/Ankara-Kalesi2.jpg", "description": "Kofi is a nice place", "from": "2016-04-04T20:00:00", "to": "2016-04-04T20:00:00"}
        place5 = {"latitude": "39.9208289", "longitude": "32.85387930000002"}
        activity5 = {"id": "123", "name": "Kizilay", "type": "visit", "place": place5, "picture_url": "https://upload.wikimedia.org/wikipedia/commons/b/b3/K%C4%B1z%C4%B1lay_Square_in_Ankara,_Turkey.JPG", "description": "Kizilay is a nice place", "from": "2016-04-04T20:00:00", "to": "2016-04-04T20:00:00"}
        place6 = {"latitude": "39.1667", "longitude": "35.6667"}
        activity6 = {"id": "1234", "name": "Ankara Kalesi", "type": "visit", "place": place6, "picture_url": "http://gezipgordum.com/wp-content/uploads/Ankara-Kalesi2.jpg", "description": "Kofi is a nice place", "from": "2016-04-04T20:00:00", "to": "2016-04-04T20:00:00"}
        activities = [activity2, activity3, activity4, activity5, activity6];
        travel = { 'city': "asd", 'from': "2016-04-04T20:00:00", 'to': "2016-04-04T20:00:00", 'activities': activities}
        return dumps( { 'travel_id': 3, 'from': "2016-04-04T20:00:00", 'to': "2016-04-04T20:00:00", 'activities': activities} )
    except:
        return dumps({'Error': 'Error occured'})
        
if __name__ == "__main__": 
    app.debug = True 
    port = int(os.environ.get("PORT", 5000))   
    app.run(port=port)
