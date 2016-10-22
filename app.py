import requests
import csv
import re
import os
from datetime import datetime

from werkzeug.exceptions import BadRequest
from flask import Flask, request, url_for
from flask_restplus import Api, Resource, fields, reqparse
from flask_sqlalchemy import SQLAlchemy

from geopy.distance import vincenty

def load_db(filename):
    result = []
    headers = None
    with open(filename) as f:
        reader = csv.reader(f)
        for row in reader:
            row = [unicode(item, 'utf-8') for item in row]
            if headers is None:
                headers = row
            else:
                result.append(dict(zip(headers, row)))
    return result

raw_places = load_db('./db/place.csv')
raw_menus = load_db('./db/menu.csv')

def make_place_db():
    indexed_menu = {}
    for menu in raw_menus:
        index = menu['RestaurantName']
        name = menu['MenuName']
        price = menu['Price']
        images = split_and_strip(menu['Prictures'])

        indexed_menu[index] = dict(
            name=name,
            price=price,
            images=images
        )
    places = []
    for place in raw_places:
        category = place['Category']
        name = place['Name']
        score = toFloat(place['Score'])
        information = place['Information']
        images = split_and_strip(place['Pictures'])
        open_time = place['OpenTime']
        close_time = place['CloseTime']
        price = place['Price']
        latitude = toFloat(place['Latitude'])
        longitude = toFloat(place['Longitude'])
        gender = place['Gender']
        weathers = map(lambda x: x.lower(), split_and_strip(place['Weather']))
        menus = indexed_menu[name] if name in indexed_menu else None
        
        recommend = split_and_strip(place['RecommendTimes'])
        recommend_times = []
        for time in recommend:
            recommend_times.append(time.split('-'))

        places.append(dict(
            category=category,
            name=name,
            score=score, 
            information=information,
            images=images,
            open_time=open_time,
            close_time=close_time,
            price=price,
            latitude=latitude,
            longitude=longitude,
            gender=gender,
            weathers=weathers,
            recommend_times=recommend_times,
            menus=menus
        ))
    return places

def split_and_strip(string):
    return map(lambda x: x.strip(), re.split('[\n,]', string))

def toInt(string):
    if len(string) == 0 or string == '-':
        return 0
    return int(string.replace(',', ''))

def toFloat(string):
    if len(string) == 0 or string == '-':
        return 0.0
    return float(string.replace(',', ''))

places = make_place_db()


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
application = app
api = Api(app)
db = SQLAlchemy(app)

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gender = db.Column(db.String(20))


user_ns = api.namespace('users', description='User operations')

user = api.model('User', dict(
    id=fields.Integer(readOnly=True, description='The user identifier (auto generated)'),
    gender=fields.String(required=True, description='The gender of user (female or male)')
))

@user_ns.route('/')
class User(Resource):
    @user_ns.doc("create_user")
    @user_ns.expect(user)
    @user_ns.marshal_with(user, code=201)
    def post(self):
        payload = api.payload
        if payload['gender'] not in ['male', 'female']:
            raise BadRequest("Gender is male or femal")
        user = UserModel(gender=payload['gender'])
        db.session.add(user)
        db.session.commit()
        return user, 201

weather_ns = api.namespace('weather', description="Weather operations")

weather = api.model('Weather', dict(
    summary=fields.String(readOnly=True, description='Current weather summary(clouds, rain, clear)'),
    temp=fields.Integer(readOnly=True, description='Current temporature in celsius')
))

@weather_ns.route('/')
class Weather(Resource):
    @weather_ns.doc('get_weather')
    @weather_ns.marshal_with(weather, code=200)
    def get(self):
        r = requests.get("http://api.openweathermap.org/data/2.5/weather?id=1846266&APPID=ded122307edfb8f2fd9c688138c4f220")
        json = r.json()
        summary = json['weather'][0]['main'].lower()
        temp = json['main']['temp'] - 273.15

        return dict(
            summary=summary,
            temp=temp
        )

place_ns= api.namespace('places', description='Place operations')

menu = api.model('Menu', dict(
    name=fields.String(readOnly=True),
    images=fields.List(fields.String),
    price=fields.String(readOnly=True)
))

place = api.model('Place', dict(
    distance=fields.Float(readOnly=True, description='Distance form here'),
    latitude=fields.Float(readOnly=True, description='Coordinates latitude'),
    longitude=fields.Float(readOnly=True, description='Coordinates longitude'),
    name=fields.String(readOnly=True, description='Name'),
    information=fields.String(readOnly=True),
    images=fields.List(fields.String),
    price=fields.String(readOnly=True),
    menus=fields.List(fields.Nested(menu)),
    score=fields.Float(readOnly=True),
    meta_score=fields.Integer(readOnly=True)
))


place_parser = reqparse.RequestParser()
place_parser.add_argument('latitude', required=True, type=float, help='Coordinates latitude')
place_parser.add_argument('longitude', required=True, type=float, help='Coordinates longitude')
place_parser.add_argument('user_id', required=True, help='User id')

@place_ns.route('/')
class Places(Resource):
    @place_ns.doc('get available place type')
    def get(self):
        return dict(types=["attraction", "accommodation", "foods"])

@place_ns.route('/<place_type>')
@place_ns.expect(place_parser)
@place_ns.param('place_type', 'Place Type')
class Place(Resource):
    @place_ns.doc('get_places')
    @place_ns.marshal_list_with(place, code=200)
    def get(self, place_type):
        args = place_parser.parse_args(strict=True)
        user_model = UserModel.query.filter_by(id=args['user_id']).one()

        latitude = args['latitude']
        longitude = args['longitude']
        gender = user_model.gender

        r = requests.get("http://api.openweathermap.org/data/2.5/weather?id=1846266&APPID=ded122307edfb8f2fd9c688138c4f220")
        json = r.json()
        weather = json['weather'][0]['main'].lower()

        return self.make_result(latitude, longitude, gender, weather, place_type)

    def make_result(self, latitude, longitude, gender, weather, place_type):
        result = []
        for place in places:
            place['distance'] = vincenty(
                    (place['latitude'], place['longitude']),
                    (latitude, longitude)).km
            place['meta_score'] = self.get_meta_score(place, gender)
            result.append(place)
        return self.filter_and_reorder_places(
                result, gender, weather, place_type)

    def filter_and_reorder_places(
            self, places, gender, weather, place_type):
        places = self.filter_by_place_type(places, place_type)
        places = self.filter_by_time(places)
        places = self.filter_by_weather(places, weather)
        places = self.sort_by_meta_score(places, gender)
        return places

    def filter_by_place_type(self, places, place_type):
        return filter(lambda x: x['category']== place_type, places)

    def filter_by_time(self, places):
        def filterfunc(x):
            if len(x['open_time'].strip()) == 0 or x['open_time'] == '-':
                return True
            startTime = x['open_time']
            endTime = x['close_time']
            return self.isNowInTimePeriod(startTime, endTime)
        return filter(filterfunc, places)

    def isNowInTimePeriod(self, startTime, endTime):
        format = "%H:%M"
        startTime = datetime.strptime(startTime, format).time()
        endTime = datetime.strptime(endTime, format).time()
        nowTime = datetime.now().time()
        if startTime < endTime:
            return nowTime >= startTime and nowTime <= endTime
        else: #Over midnight
            return nowTime >= startTime or nowTime <= endTime

    def filter_by_weather(self, places, weather):
        def filterfunc(x):
            if 'all' in x['weathers']:
                return True
            elif weather in x['weathers']:
                return True
        return filter(filterfunc, places)

    def sort_by_meta_score(self, places, gender):
        def cmp(left, right):
            return self.get_meta_score(right, gender) - self.get_meta_score(left, gender)

        return sorted(
                places,
                cmp)

    def get_meta_score(self, place, gender):
        meta_score = 0
        distance = place['distance']
        if distance < 10:
            meta_score += 300
        elif distance < 20:
            meta_score += 200
        elif distance < 40:
            meta_score += 150

        if place['gender'] == 'both':
            meta_score += 80

        if place['gender'].lower() == gender:
            meta_score += 150

        score = place['score']
        if score >= 9.5:
            meta_score += 200
        elif score >= 8.5:
            meta_score += 150
        elif score >= 7:
            meta_score += 100
        elif score >= 6:
            meta_score += 50
        elif score >= 4.8:
            meta_score += 0
        else:
            meta_score -= 200

        if 'recommend_times' in place:
            for time in place['recommend_times']:
                if len(time) != 2:
                    continue
                start, end = time
                if self.isNowInTimePeriod(start, end):
                    meta_score += 100

        return int(meta_score)





if __name__ == "__main__":
    db.create_all()
    app.debug = True
    app.run(debug=True)

