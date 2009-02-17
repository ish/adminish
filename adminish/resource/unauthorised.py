from adminish.lib import base, templating
from adminish.resource import login


class UnauthorisedPage(base.BasePage):
    """
    Unauthorised access page.
    """

    def __init__(self, errors):
        base.BasePage.__init__(self)
        self.errors = errors

    def resource_child(self, request, segments):
        return None

    @templating.page('unauthorised.html')
    def __call__(self, request):
        login_form = login.login_form(request, came_from=request.url)
        return {'errors': self.errors, 'login_form': login_form}

