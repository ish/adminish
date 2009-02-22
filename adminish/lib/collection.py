from __future__ import with_statement
from restish import resource, http, util
from restish.page import Element
import schemaish, formish

from adminish.lib import base, templating, flash

from couchish.couchish_formish_jsonbuilder import build
from pagingish.webpaging import CouchDBSkipLimitPaging, CouchDBPaging

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


class CollectionPage(base.BasePage):
    
    type = None
    label = None
    template = 'admin/items.html'
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
    


class CollectionItemPage(base.BasePage):
    
    type = None
    label = None
    template = 'admin/item.html'
    
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
        
