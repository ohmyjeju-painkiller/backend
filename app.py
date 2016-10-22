from flask import Flask, request, url_for
from flask.ext.restplus import Api, Resource

app = Flask(__name__)
application = app
api = Api(app)

@api.route('/join')
class User(Resource):
    def post(self):
        gender = request.form['gender']
        return dict(user_id="asdf")

@api.route('/weather')
class Weather(Resource):
    def get(self):
        return dict(current_weather="cloudy")

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
    app.run(debug=True)

