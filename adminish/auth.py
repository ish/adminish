"""
Authentication-related code.
"""

import cgi
from wsgiapptools import cookies

def authenticate(credentials):
    """
    Authenticate the given credentials returning a username or None.
    """
    if 'password' in credentials:
        return _authenticate_password(credentials, 'password')


def set_authenticated_username(request, username):
    """
    Automatically log in.
    """
    # Find the reqoze.who plugin that will remember the identity.
    rememberer = request.environ['repoze.who.plugins']['auth_tkt']
    # Build an identity. repoze.who seems to only *need* the username but there
    # are other bits that can go in the cookie.
    identity = {'repoze.who.userid': username}
    # Set the cookies that the remember says to set.
    cookie_cutter = cookies.get_cookie_cutter(request.environ)
    for _, cookie_header in rememberer.remember(request.environ, identity):
        cookie_cutter.set_cookie(cookie_header)


def _authenticate_password(credentials, password):
    """
    Authenticate password credentials.
    """
    if password != credentials['password']:
        return None
    return 'admin'


def make_authenticator_plugin():
    return AuthenticatorPlugin()


class AuthenticatorPlugin(object):
    """
    reqpoze.who authenticator that tries to authenticate the identity as admin
    infomy login account.
    """

    def authenticate(self, environ, identity):
        # Basic sanity check.
        if 'login' not in identity:
            return None
        # Extract the credentials from the identity.
        if 'password' in identity:
            credentials = {'username': identity['login'], 'password': identity['password']}
        else:
            return None
        # Try to authenticate the user.
        username = authenticate(credentials)
        if username is None:
            return None
        return username

