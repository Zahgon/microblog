from http import HTTPStatus

from starlette.responses import JSONResponse

# The handler that used to be registered on this blueprint for HTTPException
# is now the application wide handler installed in app/errors/handlers.py,
# which returns these JSON errors for every request made to the API.


def error_response(status_code, message=None, headers=None):
    try:
        description = HTTPStatus(status_code).phrase
    except ValueError:
        description = 'Unknown error'
    payload = {'error': description}
    if message:
        payload['message'] = message
    return JSONResponse(payload, status_code=status_code, headers=headers)


def bad_request(message):
    return error_response(400, message)
