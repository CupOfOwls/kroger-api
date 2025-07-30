# Make the KrogerAPI class available at the package level
from kroger_api.kroger_api import KrogerAPI
from . import auth
from . import utils
from .client import KrogerClient

__all__ = ['KrogerAPI', 'auth', 'utils', 'KrogerClient']  # Optional but recommended
