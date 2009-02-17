"""
restish.guard implementation.
"""

from restish import guard as restishguard

from adminish import who
from adminish.resource import unauthorised


GuardError = restishguard.GuardError


def guard(checkers):
    return restishguard.guard(checkers, error_handler=_guard_error_handler)


def _guard_error_handler(request, resource, errors):
    return unauthorised.UnauthorisedPage(errors)


def authenticated_checker():
    """
    Create an "authenticated" guard checker.
    """
    def checker(request, obj):
        if who.get_identity(request) is None:
            raise GuardError("Not logged in")
    return checker


def is_admin():
    """
    Create a "has_permission" guard checker.
    """
    def checker(request, obj):
        identity = who.get_identity(request)
        if not identity or not identity.is_admin():
            raise GuardError("Need admin permissions")
    return checker


