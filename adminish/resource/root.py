from __future__ import with_statement
import logging
import math
import clevercss
from restish import http, resource
from adminish.lib import base, collection, templating, guard
from couchish.couchish_formish_jsonbuilder import build

from formish.fileresource import FileResource
from formish.filestore import CachedTempFilestore

import couchish
from couchish.filestore import CouchDBFilestore

from operator import itemgetter

log = logging.getLogger(__name__)


class Root(base.BasePage):

    @resource.GET()
    @templating.page('root.html')
    def html(self, request):
        return {}

    @resource.child()
    def example(self, request, segments):
        return Example()

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


class Example(base.BasePage):

    @resource.GET()
    def GET(self, request):
        """
        http://localhost:8080/example?nd=1234901751220&_search=false&rows=10&page=1&sidx=url&sord=desc
        nd
        """
        C = request.environ['couchish']
        M = request.environ['adminish']['page']
        T = C.config.types['page']
        try:
            page = int(request.GET.get('page'))
        except ValueError:
            page = 0
        try:
            numrows = int(request.GET.get('rows'))
        except ValueError:
            numrows = 10
        sortkey = request.GET.get('sidx')
        reverse = request.GET.get('sord')
        if reverse == 'asc':
            reverse = False
        else:
            reverse = True
        with C.session() as S:
            items = S.docs_by_type('page')
        items = list(items)
        items = sorted(items, key=itemgetter(sortkey), reverse=reverse)

        records = len(items)
        total_pages = int(math.ceil( float(records) / int(numrows) ))
        if page > total_pages:
            page = total_pages
        start = (page-1) * numrows
        end = page * numrows
        results = {'page': int(page), 'total': int(total_pages), 'records': records}
        rows = []
        for item in items[start:end]:
            rows.append( {'id':item['url'], 'cell':[item['url'], item['title']]} )

        results['rows'] = rows

        return http.ok([('Content-Type','text/javascript'),], couchish.jsonutil.dumps(results) )

        
class PageResource(base.BasePage):

    def __init__(self, segments):
        self.segments = segments

    @resource.GET(accept='html')
    @templating.page('page.html')
    def page(self, request):
        url = '/%s'%('/'.join(self.segments))
        C = request.environ['couchish']
        with C.session() as S:
            page = list(S.view('page/by_url',key=url,include_docs=True))
        return {'page': page[0].doc}




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

