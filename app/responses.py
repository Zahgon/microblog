"""Response helpers."""
from starlette.responses import RedirectResponse


def redirect(location, code=302, headers=None):
    """Return a response that redirects the client to the given location."""
    return RedirectResponse(location, status_code=code, headers=headers)
