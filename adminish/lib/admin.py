from __future__ import with_statement
import pkg_resources
import logging
from restish import resource, http, util
from restish.page import Element
import schemaish, formish
import couchish, couchdb

from adminish.lib import base, templating, flash

from couchish.couchish_formish_jsonbuilder import build
from pagingish.webpaging import CouchDBSkipLimitPaging, CouchDBPaging
import markdown

log = logging.getLogger(__name__)



def confirm_doc_and_rev(src, dest):
    """
    Confirm that the src and dest docs match in terms of id and rev, raising an
    HTTP exception on failure.

    A BadRequestError is raised if the ids do not match. A ConflictError is
    raised if the revs do not match.
    """
    if src['_id'] != dest['_id']:
        raise BadRequestError('incorrect id')
    if src['_rev'] != dest['_rev']:
        raise ConflictError('rev is out of date')


class Markdown(base.BasePage):

    @resource.POST()
    @templating.page('/admin/preview.html')
    def GET(self, request):
        return {'data':markdown.markdown(request.POST.get('data',''))}


class Admin(base.BasePage):
    
    @resource.GET()
    @templating.page('/admin/root.html')
    def GET(self, request):
        C = request.environ['couchish']
        model_metadata =  request.environ['adminish']
        return {'model_metadata':model_metadata}

    @resource.child('_markdown')
    def markdown(self, request, segments):
        return Markdown()

    @resource.child('{type}')
    def items(self, request, segments, type=None):
        return Page(type=type)

    @resource.child('{type}/{id}')
    def item(self, request, segments, type=None, id=None):
        return ItemPage(id, type=type)


class Page(base.BasePage):
    
    type = None
    label = None
    template = '/admin/items.html'
    item_resource = None

    def __init__(self, type=None, label=None, template=None, item_resource=None):
        if type is not None:
            self.type = type
        if label is not None:
            self.label = label
        if template is not None:
            self.template = template
        if item_resource is not None:
            self.item_resource = item_resource


    @resource.GET()
    def html(self, request, form=None):
        C = request.environ['couchish']
        defn = C.config.types[self.type]
        if form is None:
            form = build(defn, C.db)
            
        return self.render_page(request, form)

    def render_page(self, request, form):
        C = request.environ['couchish']
        M = request.environ['adminish'][self.type]
        T = C.config.types[self.type]
        ## XXX Here we have two options for paging - a non efficient one with page ranges and an efficient one with only next prev
        pagingdata = CouchDBSkipLimitPaging(C.session().view, '%s/all'%self.type, '%s/all_count'%self.type, include_docs=True)
        #pagingdata = CouchDBPaging(C.session().view, '%s/all'%self.type, include_docs=True)
        pagingdata.load_from_request(request)
        items = [item.doc for item in pagingdata.docs]

        def page_element(name):
            E = self.element(request, name)
            if isinstance(E, Element):
                E = util.RequestBoundCallable(E, request)
            return E
        data = {'form': form, 'items': items, 'pagingdata': pagingdata, 'metadata': M,'element':page_element, 'types':T} 
        page = templating.render(request, M['templates']['items'], data)
        return http.ok([('Content-Type', 'text/html')], page)
    
    @resource.POST()
    def POST(self, request):
        C = request.environ['couchish']
        defn = C.config.types[self.type]
        form = build(defn, C.db)
        try:
            data = form.validate(request)
        except formish.FormError:
            return self.html(request, form)
        data.update({'model_type':self.type})
        with C.session() as S:
            S.create(data)
        flash.add_message(request.environ, 'item created.', 'success')
        return http.see_other(request.url)
    
    def resource_child(self, request, segments):
        return self.item_resource(segments[0]), segments[1:]
    

class ItemPage(base.BasePage):
    
    type = None
    label = None
    template = '/admin/item.html'
    
    def __init__(self, id, type=None, label=None, template=None):
        self.id = id
        if type is not None:
            self.type = type
        if label is not None:
            self.label = label
        if template is not None:
            self.template = template
    
    def get_form(self, request):        
        C = request.environ['couchish']
        defn = C.config.types[self.type]
        form = build(defn, C.db, add_id_and_rev=True)
        form.add_action(self.delete_item, 'delete')
        form.add_action(self.update_item, 'submit')
        return form

    @resource.GET()
    def html(self, request, form=None):
        C = request.environ['couchish']
        if form is None:
            form = self.get_form(request)
            with C.session() as S:
                form.defaults = S.doc_by_id(self.id)
        return self.render_page(request, form)
        
    def render_page(self, request, form):
        C = request.environ['couchish']
        M = request.environ['adminish'][self.type]
        def page_element(name):
            E = self.element(request, name)
            if isinstance(E, Element):
                E = util.RequestBoundCallable(E, request)
            return E
        data = {'form': form, 'metadata': M,'element':page_element}
        page = templating.render(request, M['templates']['item'], data)
        return http.ok([('Content-Type', 'text/html')], page)
            
    @resource.POST()
    def POST(self, request):
        form = self.get_form(request)      
        return form.action(request)

    def delete_item(self, request, form):
        C = request.environ['couchish']
        with C.session() as S:
            doc = S.doc_by_id(self.id)
            S.delete(doc)
        flash.add_message(request.environ, 'item deleted.', 'success')
        return http.see_other(request.url.parent())
    
    def update_item(self, request, form):
        C = request.environ['couchish']
        try:
            data = form.validate(request)
        except formish.FormError:
            return self.html(request, form)
        with C.session() as S:
            doc = S.doc_by_id(self.id)
            confirm_doc_and_rev(doc, data)
            doc.update(data)
        flash.add_message(request.environ, 'item updated.', 'success')
        return http.see_other(request.url.parent())
        

def make_adminish_config(types):
    allmetadata = {}
    for type, data in types.items():
        metadata = {}
        m = data.get('metadata',{})
        metadata['labels'] = m.get('labels',{})
        metadata['labels']['singular'] = m.get('labels',{}).get('singular', type.title())
        metadata['labels']['plural'] = m.get('labels',{}).get('plural', '%ss'%type.title())
        metadata['templates'] = m.get('templates',{})
        metadata['templates']['item'] = m.get('templates',{}).get('item', '/admin/item.html')
        metadata['templates']['items'] = m.get('templates',{}).get('items','/admin/items.html')
        try:
            metadata['templates']['items-table'] = m.get('templates',{})['items-table']
            for n, entry in enumerate(metadata['templates']['items-table']):
                metadata['templates']['items-table'][n]['label'] = entry.get('label')
                metadata['templates']['items-table'][n]['value'] = entry.get('value')
        except KeyError:
            pass
        allmetadata[type] = metadata

    return allmetadata
            

def make_couchish_store(app_conf):

    views_filename = _couchish_config_filename('views.yaml')
    print views_filename
    MODEL_NAMES = ['page', 'tour', 'category', 'leader']
    return couchish.CouchishStore(
        couchdb.Database(app_conf['couchish.db.url']),
        couchish.Config.from_yaml(
            dict((name,_model_filename(name)) for name in MODEL_NAMES),
            _couchish_config_filename('views.yaml')))


def _model_filename(model_name):
    return _couchish_config_filename('%s.yaml'%model_name)


def _couchish_config_filename(filename):
    return pkg_resources.resource_filename('adminish.model', filename)


