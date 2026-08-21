from starlette.responses import PlainTextResponse

from app import db
from app.api.errors import error_response as api_error_response
from app.responses import redirect
from app.templating import render_template


def _accept_quality(request, mimetype):
    """Return the quality the client gives to a mime type."""
    best = 0.0
    for part in request.headers.get('accept', '').split(','):
        part = part.strip()
        if not part:
            continue
        pieces = part.split(';')
        value = pieces[0].strip()
        quality = 1.0
        for piece in pieces[1:]:
            piece = piece.strip()
            if piece.startswith('q='):
                try:
                    quality = float(piece[2:])
                except ValueError:
                    quality = 0.0
        if value == mimetype or value == '*/*' or \
                (value.endswith('/*') and
                 mimetype.startswith(value[:-1])):
            best = max(best, quality)
    return best


def wants_json_response(request):
    return _accept_quality(request, 'application/json') >= \
        _accept_quality(request, 'text/html')


def wants_api_response(request):
    return request.url.path.startswith('/api')


async def not_found_error(request, error):
    if wants_api_response(request) or wants_json_response(request):
        return api_error_response(404)
    return render_template('errors/404.html', status_code=404)


async def internal_error(request, error):
    db.session.rollback()
    if wants_api_response(request) or wants_json_response(request):
        return api_error_response(500)
    return render_template('errors/500.html', status_code=500)


async def http_exception(request, error):
    """Handle the HTTP errors raised by the views."""
    if error.status_code == 404:
        return await not_found_error(request, error)
    if error.status_code == 500:
        return await internal_error(request, error)
    if wants_api_response(request):
        return api_error_response(error.status_code,
                                  headers=getattr(error, 'headers', None))
    return PlainTextResponse(error.detail, status_code=error.status_code,
                             headers=getattr(error, 'headers', None))


async def auth_redirect(request, error):
    """Send anonymous users to the login page."""
    return redirect(error.location)
