"""Provider fetchers: log into a utility portal and download the latest bill PDF.

Importing this package registers the built-in fetchers (currently the `example`
template). Add a provider by dropping a `fetchers/<name>.py` module that defines a
`@register`-decorated `BaseFetcher` subclass, then importing it here.
"""

from fetchers.base import (
    BaseFetcher,
    ProviderCredentials,
    available,
    get_fetcher_class,
    register,
)

# Import provider modules so their @register decorators run.
from fetchers import example_provider  # noqa: E402,F401

__all__ = [
    "BaseFetcher",
    "ProviderCredentials",
    "available",
    "get_fetcher_class",
    "register",
]
