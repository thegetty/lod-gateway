from flask import Response

from app.di import DI

DEFAULT_HEADERS = {"Server": "MART/1.0", "Access-Control-Allow-Origin": "*"}


def errorResponse(error):
    return Response(
        error[1], status=error[0], headers={**{"X-Error": error[1]}, **DEFAULT_HEADERS}
    )


def instantiateDatabase():
    error = None
    response = None

    database = DI.get("database")
    if database:
        connection = database.connect(autocommit=True)
        if connection:
            DI.set("connection", connection)
        else:
            error = (500, "Unable to establish a database connection!")
    else:
        error = (500, "Unable to obtain the database handler!")

    if error:
        response = errorResponse(error)

    return database, connection, response
