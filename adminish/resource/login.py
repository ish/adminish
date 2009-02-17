# framework
import schemaish
import formish
from restish import page, resource
import validatish

# Application
from adminish.lib import base, templating

from formish import validation, widgets, Form


def make_form(request, *args, **kwargs):
    kwargs['renderer'] = request.environ['restish.templating.renderer']
    return Form(*args, **kwargs)


class LoginStructure(schemaish.Structure):
    login = schemaish.String(validator=validatish.Required())
    password = schemaish.String(validator=validatish.Required())



def login_form(request, came_from=None):
    """
    Create a login form with an optional "came_from" URL.

    If came_from is not specified then a suitable URL is determined by:
      1. Use the 'came_from' query parameter if available.
      2. Use the referrer URL in the HTTP request header.
      3. Use the root of the web server.
    """
    form = make_form(request,LoginStructure(), action_url=request.url.sibling('login_handler'))
    form['password'].widget = formish.Password()
    return form


class LoginResource(base.BasePage):

    @page.element('form_login')
    def form_login(self, request):
        form = login_form(request)
        form.defaults['login'] = request.GET.get('login')
        form.defaults['password'] = request.GET.get('password')
        return form

    @page.element('form_forgotten_password')
    def form_forgotten_password(self, request):
        form = make_form(request,ForgottenPasswordStructure())
        return form
    
    @resource.GET()
    def html(self, request):
        return self.render_page(request)

    @resource.POST()
    def POST(self, request):
        # Check which form has been posted
        form_name = request.POST.get('__formish_form__',None)
        if form_name == 'form_login':
            raise Exception("This should have been handled by repoze.who")
        
    @templating.page('/login/loginpage.html')
    def render_page(self, request, args={}):
        return args


class LogoutResource(base.BasePage):
    """
    Logout resource.
    """

    @resource.GET()
    @templating.page('logout.html')
    def html(self, request):
        return {}

    @resource.POST()
    def post(self, request):
        raise Exception("This should have been handled by repoze.who")

