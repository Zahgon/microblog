"""Query string parameters.

``request.args.get(name, default, type=int)`` ignored the values it could not
convert and returned the default, while FastAPI rejects the request with a
validation error. These annotated types restore the lenient behaviour of the
Flask version, so that a hand written URL such as ``/explore?page=x`` shows the
first page instead of an error.
"""
from typing import Annotated

from pydantic import BeforeValidator


def _lenient(converter, default):
    def convert(value):
        if value is None:
            return default
        try:
            return converter(value)
        except (TypeError, ValueError):
            return default
    return convert


Page = Annotated[int, BeforeValidator(_lenient(int, 1))]
PerPage = Annotated[int, BeforeValidator(_lenient(int, 10))]
Since = Annotated[float, BeforeValidator(_lenient(float, 0.0))]
