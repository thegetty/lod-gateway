import sys
import datetime

# import our utility functions (get, has, debug, repeater, sprintf, etc)
from app.utilities import *

from flask import Flask

app = Flask(__name__)

@app.route("/")
def welcome():
	now = datetime.datetime.now()
	
	return sprintf("Welcome to the Museum Linked Art Data Service at %02d:%02d:%02d on %02d/%02d/%04d" % (now.hour, now.minute, now.second, now.month, now.day, now.year))
	# return "Hello"

# if __name__ == "__main__":
#    # make debug an environment variable
#    app.run(host="0.0.0.0", port=int("5100"), debug=True)