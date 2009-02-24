import logging
import markdown
from restish import resource
from adminish.lib import base, admin, templating




log = logging.getLogger(__name__)


class Admin(base.BasePage):
    
    @resource.GET()
    @templating.page('admin/root.html')
    def GET(self, request):
        C = request.environ['couchish']
        model_metadata =  request.environ['adminish']
        return {'model_metadata':model_metadata}

    @resource.child('_markdown')
    def markdown(self, request, segments):
        return Markdown()

    @resource.child('{type}')
    def items(self, request, segments, type=None):
        return admin.Page(type=type)

    @resource.child('{type}/{id}')
    def item(self, request, segments, type=None, id=None):
        return admin.ItemPage(id, type=type)

class Markdown(base.BasePage):

    @resource.POST()
    @templating.page('admin/preview.html')
    def GET(self, request):
        return {'data':markdown.markdown(request.POST.get('data',''))}
