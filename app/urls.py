"""URL generation.

``url_for()`` builds URLs from the name of a route, in the same way Flask did
it from the name of a view function. Route names keep the ``blueprint.view``
format used by the Flask version of the application, so templates and models
did not have to change the endpoints they reference.
"""
from urllib.parse import urlencode, urljoin

from starlette.routing import NoMatchFound

from app.context import get_request
from app.state import state


def _find_route(endpoint):
    for route in state.app.routes:
        if getattr(route, 'name', None) == endpoint:
            return route
    return None


def _base_url():
    request = get_request()
    if request is not None:
        return str(request.base_url)
    server_name = state.config.get('SERVER_NAME')
    if not server_name:
        raise RuntimeError(
            'Unable to build an external URL without a request. Set the '
            'SERVER_NAME configuration option.')
    scheme = state.config.get('PREFERRED_URL_SCHEME', 'http')
    return f'{scheme}://{server_name}/'


def url_for(endpoint, **values):
    """Build the URL of a route, given its name and its parameters."""
    external = values.pop('_external', False)
    anchor = values.pop('_anchor', None)
    if state.app is None:
        raise RuntimeError('The application has not been created yet.')

    route = _find_route(endpoint)
    if route is None:
        raise NoMatchFound(endpoint, values)

    convertors = getattr(route, 'param_convertors', None) or {}
    path_params = {name: values.pop(name) for name in list(values)
                   if name in convertors}
    url = str(state.app.router.url_path_for(endpoint, **path_params))

    query = urlencode([(key, value) for key, value in values.items()
                       if value is not None], doseq=True)
    if query:
        url = f'{url}?{query}'
    if anchor is not None:
        url = f'{url}#{anchor}'
    if external:
        url = urljoin(_base_url(), url)
    return url
