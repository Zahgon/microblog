"""Template rendering.

The Jinja environment is created here with the same globals that Flask and its
extensions used to install, so the templates of the application did not need to
be rewritten.
"""
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.responses import HTMLResponse

from app.context import g, get_flashed_messages
from app.i18n import gettext, ngettext, get_locale
from app.login import current_user
from app.moment import moment
from app.state import state
from app.urls import url_for

TEMPLATE_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'templates')

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIRECTORY),
    autoescape=select_autoescape(
        enabled_extensions=('html', 'htm', 'xml'),
        default_for_string=False, default=False),
    trim_blocks=False,
    lstrip_blocks=False,
    extensions=['jinja2.ext.i18n'],
)
# the "new style" callables make the translated string a Markup object when
# the template is autoescaped, so that the placeholders of a translation can
# be given HTML fragments, as _post.html does
env.install_gettext_callables(gettext, ngettext, newstyle=True)
env.globals.update({
    'url_for': url_for,
    'get_flashed_messages': get_flashed_messages,
    'current_user': current_user,
    'g': g,
    'moment': moment,
    'config': state.config,
    'get_locale': get_locale,
})


def render_to_string(template_name, **context):
    """Render a template and return it as a string."""
    return env.get_template(template_name).render(**context)


def render_template(template_name, status_code=200, headers=None, **context):
    """Render a template and return it as an HTML response."""
    return HTMLResponse(render_to_string(template_name, **context),
                        status_code=status_code, headers=headers)
