import logging
import clevercss
from restish import http, resource
from adminish.lib import base, collection, templating, guard
from couchish.couchish_formish_jsonbuilder import build

from formish.fileresource import FileResource
from formish.filestore import CachedTempFilestore

import couchish
from couchish.filestore import CouchDBFilestore

log = logging.getLogger(__name__)

#class Root(resource.Resource):
#    @resource.GET()
#    @templating.page('root.html')
#    def html(self, request):
#        C = request.environ['couchish']
#        page =  C.config.types['page']
#        return {'form':build(page)}

class Root(base.BasePage):

    @guard.guard(guard.is_admin())
    @resource.child()
    def admin(self, request, segments):
        return Admin()
    
    @resource.child(resource.any)
    def page(self, request, segments):
        return PageResource(segments), ()

    @resource.child('filehandler')
    def filehandler(self, request, segments):
        tempfilestore = CachedTempFilestore(name='tmp')
        cdbfilestore = CouchDBFilestore(request.environ['couchish'], name='cdb')
        return FileResource(filestores=[cdbfilestore, tempfilestore])

    #####
    # clevercss
    @resource.child('ccss/{file}')
    def child_ccss(self, request, segments, file=None):
        return lambda request: self.css(request, file=file)

    def css(self, request, file):
        if file is None:
            return
        ccss = templating.render(request,'ccss/%s'%file, {})
        css = clevercss.convert(ccss)
        return http.ok([('Content-Type', 'text/css')], css)

    @resource.child('ccsss/{file}')
    def child_ccsss(self, request, segments, file=None):
        return lambda request: self.csss(request, file=file)

    def csss(self, request, file):
        if file is None:
            return
        ccss = templating.render(request,'ccss/%s'%file, {})
        return http.ok([],ccss)



class Admin(base.BasePage):
    
    @resource.GET()
    @templating.page('admin/root.html')
    def GET(self, request):
        C = request.environ['couchish']
        model_metadata =  request.environ['adminish']
        return {'model_metadata':model_metadata}

    @resource.child('{type}')
    def items(self, request, segments, type=None):
        return collection.CollectionPage(type=type)

    @resource.child('{type}/{id}')
    def item(self, request, segments, type=None, id=None):
        return collection.CollectionItemPage(id, type=type)

