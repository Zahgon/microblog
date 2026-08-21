"""Internationalization support.

Flask-Babel is replaced here by direct use of the Babel library. The locale of
the current request is kept in a context variable that the request context
middleware sets on every request.
"""
import os
from contextvars import ContextVar

from babel import Locale, negotiate_locale
from babel.support import Translations, LazyProxy

from app.state import state
from app.context import get_request

DEFAULT_LOCALE = 'en'
TRANSLATION_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'translations')

_locale_ctx = ContextVar('microblog_locale', default=None)
_translations_cache = {}


def parse_accept_language(header):
    """Return the languages of an Accept-Language header, best first."""
    languages = []
    for index, part in enumerate(header.split(',')):
        part = part.strip()
        if not part:
            continue
        pieces = part.split(';')
        language = pieces[0].strip()
        quality = 1.0
        for piece in pieces[1:]:
            piece = piece.strip()
            if piece.startswith('q='):
                try:
                    quality = float(piece[2:])
                except ValueError:
                    quality = 0.0
        languages.append((language, quality, index))
    languages.sort(key=lambda item: (-item[1], item[2]))
    return [language for language, quality, index in languages if quality > 0]


def select_locale():
    """Pick the best supported locale for the current request."""
    languages = list(state.config.get('LANGUAGES') or [DEFAULT_LOCALE])
    request = get_request()
    if request is not None:
        preferred = parse_accept_language(
            request.headers.get('accept-language', ''))
        matched = negotiate_locale(preferred, languages, sep='-')
        if matched:
            return Locale.parse(matched, sep='-')
    return Locale.parse(languages[0] if languages else DEFAULT_LOCALE, sep='-')


def set_locale(locale):
    """Bind a locale to the current context, returning the reset token."""
    return _locale_ctx.set(locale)


def reset_locale(token):
    _locale_ctx.reset(token)


def get_locale():
    """Return the locale in use, selecting one if it has not been set yet."""
    locale = _locale_ctx.get()
    if locale is None:
        locale = select_locale()
        _locale_ctx.set(locale)
    return locale


def get_translations():
    locale = get_locale()
    key = str(locale)
    translations = _translations_cache.get(key)
    if translations is None:
        translations = Translations.load(TRANSLATION_DIRECTORY, [locale],
                                         'messages')
        _translations_cache[key] = translations
    return translations


def gettext(string, **variables):
    translated = get_translations().gettext(string)
    return translated % variables if variables else translated


def ngettext(singular, plural, num, **variables):
    variables.setdefault('num', num)
    translated = get_translations().ngettext(singular, plural, num)
    return translated % variables


def lazy_gettext(string, **variables):
    """A version of ``gettext()`` that is evaluated when it is rendered."""
    return LazyProxy(gettext, string, enable_cache=False, **variables)


_ = gettext
_l = lazy_gettext
