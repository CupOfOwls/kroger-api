# Make the KrogerAPI class available at the package level
from kroger_api.kroger_api import KrogerAPI
from . import auth
from . import utils
from . import validation
from .client import KrogerClient
from .errors import (
    KrogerAPIError,
    ConfigurationError,
    InvalidParameterError,
    NotAuthenticatedError,
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    BadRequestError,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    RateLimitError,
    InternalServerError,
    InvalidResponseError,
)

__all__ = [
    'KrogerAPI', 'auth', 'utils', 'validation', 'KrogerClient',
    'KrogerAPIError', 'ConfigurationError', 'InvalidParameterError', 'NotAuthenticatedError',
    'APIConnectionError', 'APITimeoutError', 'APIStatusError', 'BadRequestError',
    'AuthenticationError', 'PermissionDeniedError', 'NotFoundError', 'RateLimitError',
    'InternalServerError', 'InvalidResponseError',
]
