from flask import Flask
from flask_migrate import Migrate
from models import db, User, Product, Favorite, BrowseHistory, ClickHistory, SearchHistory

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'your_database_uri'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run()