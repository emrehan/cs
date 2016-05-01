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
import traceback
import grequests

day_categories = set([line.rstrip('\n') for line in open('day_categories.txt')])
night_categories = set([line.rstrip('\n') for line in open('night_categories.txt')])
food_categories = set([line.rstrip('\n') for line in open('food_categories.txt')])

### FUNCTIONS ###

def get_bulk_venues(access_token, venue_ids, batch):
    size = 10
    url = 'https://api.foursquare.com/v2//venues/'
    params = "?oauth_token=" + access_token + "&v=20160417"

    request_urls = list(map(lambda i: url + i + params, venue_ids[batch*size:(batch+1)*size]))

    candidate_venues_a = (grequests.get(u, timeout=3) for u in request_urls)
    candidate_venues_b = grequests.map(candidate_venues_a)
    candidate_venues_c = filter(None, candidate_venues_b)
    candidate_venues_d = list(map(lambda r: r.json()['response']['venue'], candidate_venues_c))

    print('Debug: Candidate venues are ' + str(candidate_venues_b))

    result_venues = []
    for candidate_venue in candidate_venues_d:
        categories = set(map(lambda categories: categories['name'], candidate_venue['categories']))
        allocations = []
        if len(categories.intersection(day_categories)) > 0:
            allocations.append('day')
        
        if len(categories.intersection(night_categories)) > 0:
            allocations.append('night')
        
        if len(categories.intersection(food_categories)) > 0:
            allocations.append('food')

        if len(allocations) > 0:
            venue = {}
            venue['type'] = 'visit'
            venue['allocations'] = allocations
            venue['id'] = candidate_venue['id']
            venue['name'] = candidate_venue['name']
            if candidate_venue['photos']['count'] > 0:
                prefix = candidate_venue['photos']['groups'][0]['items'][0]['prefix']
                suffix = candidate_venue['photos']['groups'][0]['items'][0]['suffix']
                venue['picture_url'] = prefix + '500x300' + suffix
            else:
                venue['picture_url'] = 'http://www.fb-coverz.com/covers/preview/travel.png'

            result_venues.append(venue)
    print( 'Debug: Returned ' + str(len(result_venues)) + ' candidate venues: ' + str(result_venues))
    return result_venues

def get_venues_for_day(access_token, venue_ids, day):
    scheduled_types = ['day', 'day', 'food', 'day', 'day', 'food', 'night']
    scheduled_venues = []
    candidate_venues = []

    # venue_ids = [line.rstrip('\n') for line in open('recommendations.txt')]

    batch = 0
    while(len(scheduled_types) > len(scheduled_venues)):
        next_type = scheduled_types[len(scheduled_venues)]
        candidate_index = 0
        candidate_count = len(candidate_venues)

        is_added = False
        for venue in candidate_venues:
            if next_type in venue['allocations']:
                venue['from'] = day
                venue['to'] = day
                scheduled_venues.append(venue)
                candidate_venues.remove(venue)
                is_added = True
                break

        if is_added == False:
            candidate_venues += get_bulk_venues(access_token, venue_ids, 0)
            batch += 1
    return scheduled_venues


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
        return dumps( {'travel': travel.id} )

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
        cities = []
        with open('city_names.txt') as f:
            lines = f.readlines()
            for line in lines:
                cities.append(line)


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

            prePath = "checkins/"
            cityName = city + "/"
            checkinsFolderName = "expert_checkins/"
            expertsCategoryTFFileName = "expert_categories.csv"
            expertIDsFileName = "expert_ids.txt"
            categoriesFileName = "categories.csv"
            delimiter = ","

            categoriesFilePath = prePath + categoriesFileName
            expertsFilePath = prePath + cityName + expertsCategoryTFFileName
            expertIDsFilePath = prePath + cityName + expertIDsFileName
            expertCheckinsPrefix = prePath + cityName + checkinsFolderName

            # Create TF-IDF vector of the user
            userCategoryTFDictionary = {}

            data = json.loads(r.text)
            count = data["response"]["checkins"]["count"]
            items = data["response"]["checkins"]["items"]

            for item in items:
                categories = item["venue"]["categories"]
                for category in categories:
                    categoryName = category["name"]
                    if categoryName in userCategoryTFDictionary:
                        userCategoryTFDictionary[categoryName] += 1
                    else:
                        userCategoryTFDictionary[categoryName] = 1

            for key, value in userCategoryTFDictionary.items():
                userCategoryTFDictionary[key] = float(value) / count

            categoriesFile = open(categoriesFilePath, "r")
            categoryLines = categoriesFile.readlines()
            userCategoryTFIDFs = []


            for line in categoryLines:
                tokens = line.split(delimiter)
                categoryName = tokens[0]

                if categoryName in userCategoryTFDictionary:
                    categoryTF = userCategoryTFDictionary[categoryName]
                else:
                    categoryTF = 0

                categoryCheckinCount = int(tokens[1])
                categoryIDF = 1.0 / categoryCheckinCount
                userCategoryTFIDFs.append(categoryTF * categoryIDF)

            # Iterate through experts to find similarities
            expertsFile = open(expertsFilePath, "r")
            expertIDsFile = open(expertIDsFilePath, "r")
            expertsFileLines = expertsFile.readlines()
            IDs = expertIDsFile.readlines()
            expertCosineSimilarities = {}

            for index, line in enumerate(expertsFileLines):
                expertCategoryTFs = line.split(delimiter)
                categoryCheckinCount = float(categoryLines[index].split(delimiter)[1])
                expertCategoryTFIDFs = [float(numeric_string) / categoryCheckinCount for numeric_string in
                                        expertCategoryTFs]
                cosineSimilarity = 1 - spatial.distance.cosine(userCategoryTFIDFs, expertCategoryTFIDFs)
                if cosineSimilarity > 0:
                    expertID = IDs[index].split('\n')[0]
                    expertCosineSimilarities[expertID] = cosineSimilarity

            estimatedRankings = {}
            # Find estimated rankings
            for expert, similarity in expertCosineSimilarities.items():
                expertCheckinsPath = expertCheckinsPrefix + expert + ".csv"
                checkinsFile = open(expertCheckinsPath, "r")
                lines = checkinsFile.readlines()

                for line in lines:
                    tokens = line.split(delimiter)
                    venueId = tokens[0]
                    venueCheckinCount = float(tokens[1])
                    estimatedRanking = similarity * venueCheckinCount

                    # TODO Need decision?
                    if venueId in estimatedRankings:
                        estimatedRankings[venueId] += estimatedRanking
                    else:
                        estimatedRankings[venueId] = estimatedRanking

            sortedEstimatedRankings = sorted(estimatedRankings.items(), key=operator.itemgetter(1))
            sortedEstimatedRankings.reverse()
            venue_ids = list(map(lambda e: e[0], sortedEstimatedRankings))
            return dumps({'travel_id': 42, 'from': ffrom.strftime(timeFormat), 'to': to.strftime(timeFormat), 'activities': get_venues_for_day(access_token, venue_ids, ffrom)})
    except:
        traceback.print_exc()
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
        traceback.print_exc()
        return dumps({'Error': 'Error occured'})
        
if __name__ == "__main__": 
    app.debug = True 
    port = int(os.environ.get("PORT", 5000))   
    app.run(port=port)
