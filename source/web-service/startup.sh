#!/bin/bash
export FLASK_ENV=development
export FLASK_DEBUG=1
export FLASK_APP=/app/startup.py

flask run --host=0.0.0.0 --port=5100