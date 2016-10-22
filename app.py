import requests
from werkzeug.exceptions import BadRequest
from flask import Flask, request, url_for
from flask_restplus import Api, Resource, fields
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
application = app
api = Api(app)
db = SQLAlchemy(app)

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gender = db.Column(db.String(20))

db.create_all()

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
        print json
        summary = json['weather'][0]['main'].lower()
        temp = json['main']['temp'] - 273.15

        return dict(
            summary=summary,
            temp=temp
        )

@api.route('/users/<user_id>/types')
class Types(Resource):
    def get(self, user_id):
        return dict(types=["attractions", "accommodations", "foods"])

@api.route('/users/<user_id>/types/<type>')
class Locations(Resource):
    def get(self, user_id, type):
        return dict(
            locations=[
                dict(id="18041", name="Art And Jeju", photo=url_fr("static", filename="art_and_jeju.jpg"))
            ]
        )

@api.route('/users/<user_id>/locations/<location_id>')
class Location(Resource):
    def get(self, user_id, location_id):
        return dict(
            photos=[
                url_fr("static", filename="art_and_jeju.jpg"),
                url_fr("static", filename="art_and_jeju2.jpg")
            ],
            information="The Jeju Museum of Art is surrounded by the beautiful and pristine nature of Jeju. The museum is the epicenter of Jeju art and reflects the local culture, colors and sounds of the island. It is a center at which locals and tourists can appreciate historical and recent artworks at its permanent exhibition halls, special exhibition hall and outdoor gallery. The Chang Ree-suok Hall displays 110 artworks made by the major Korean artist Chang Ree-suok. The museum also hosts various cultural and art programs.",
            bus=[
                dict(
                    number=100,
                    station=[100,100],
                    where=-2,
                    remainTime="5 min"
                )
            ],
            taxi=dict(
                expectedTime="20 min",
                price="10000 won"
            )
        )





if __name__ == "__main__":
    app.debug = True
    app.run(debug=True)

