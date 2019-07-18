import sys
import datetime
import json
import hashlib

# import our utility functions (get, has, debug, repeater, sprintf, etc)
from app.utilities import *
from app.database import Database

from flask import Flask, Response

from app.routes.activity import activity
from app.routes.records import records

app = Flask(__name__)
app.register_blueprint(activity)
app.register_blueprint(records)

@app.route("/")
def welcome():
	# return "Hello"
	
	now = datetime.datetime.now()
	
	body = sprintf("Welcome to the Museum Linked Art Data Service at %02d:%02d:%02d on %02d/%02d/%04d" % (now.hour, now.minute, now.second, now.month, now.day, now.year))
	
	return Response(body, status=200)