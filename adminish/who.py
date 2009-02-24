
class Identity(object):

    def __init__(self, user):
        self.username = user['username']

    def is_admin(self):
        return self.username=='admin'


def get_identity(request_or_environ):
    """
    Return the identity object or None.
    """
    if isinstance(request_or_environ, dict):
        environ = request_or_environ
    else:
        environ = request_or_environ.environ
    who_identity = environ.get('repoze.who.identity')
    if who_identity is None:
        return None
    return who_identity.get('adminish')


def make_metadata_plugin(*a, **k):
    return MetadataPlugin()


class MetadataPlugin(object):
    """
    repoze.who metadata plugin that populates the identity with basic
    information about the authenticated user.
    """

    def add_metadata(self, environ, identity):
        # Lookup the user information.
        userid = identity.get('repoze.who.userid')
        try:
            user = {'username':'admin'}
            identity['adminish'] = Identity(user)
        except client.NotFoundError:
            raise Exception("Looks like the current user's been removed from the database. Clean out your cookies and try again.")

