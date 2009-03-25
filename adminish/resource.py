from __future__ import with_statement
import logging
from restish import resource, http, util, templating, page
import schemaish, formish
from restish import url

from wsgiapptools import flash

from couchish.couchish_formish_jsonbuilder import build
from pagingish.webpaging import CouchDBSkipLimitPaging, CouchDBPaging
from adminish import md
import categories

from breve.tags.html import tags as T
from breve.flatten import flatten

log = logging.getLogger(__name__)

def make_form(request, *args, **kwargs):
    kwargs['renderer'] = request.environ['restish.templating'].renderer
    return Form(*args, **kwargs)

class FlashMessagesElement(page.Element):

    def __call__(self, request):
        messages = flash.get_messages(request.environ)
        if not messages:
            return ''
        return templating.render(request, 'flash_messages.html', {'messages': messages})


class BasePage(page.Page):
    @page.element('flash_message')
    def flash_message(self, request):
        """
        Return a flash message box element.
        """
        return FlashMessagesElement() 


def confirm_doc_and_rev(src, dest):
    """
    Confirm that the src and dest docs match in terms of id and rev, raising an
    HTTP exception on failure.

    A BadRequestError is raised if the ids do not match. A ConflictError is
    raised if the revs do not match.d
    """
    if src['_id'] != dest['_id']:
        raise BadRequestError('incorrect id')
    if src['_rev'] != dest['_rev']:
        raise ConflictError('rev is out of date')


class Markdown(BasePage):

    @resource.POST()
    @templating.page('/adminish/preview.html')
    def GET(self, request):
        return {'data':md.md(request.POST.get('data',''))}


class Admin(BasePage):
    
    @resource.GET()
    @templating.page('/adminish/root.html')
    def GET(self, request):
        C = request.environ['couchish']
        model_metadata =  request.environ['adminish']
        return {'model_metadata':model_metadata}

    @resource.child('_markdown')
    def markdown(self, request, segments):
        return Markdown()

    @resource.child()
    def categories(self, request, segments):
        return Categories()

    @resource.child('{type}')
    def items(self, request, segments, type=None):
        return Page(type=type)

    @resource.child('{type}/{id}')
    def item(self, request, segments, type=None, id=None):
        return ItemPage(id, type=type)


class Categories(BasePage):

    @resource.GET()
    def GET(self, request):
        return self.html(request)

    @templating.page('/adminish/facets.html')
    def html(self, request, form=None):
        C = request.environ['couchish']
        facets = dict([(t['facet']['path'],t) for k, t in C.config.types.items() if k.startswith('facet_')])
        return {'facets': facets}

    @resource.child('{facet}')
    def facet(self, request, segments, facet=None):
        return self.render_facet(request, segments, facet)

    @resource.child('{facet}/{category_path}')
    def facet_categories(self, request, segments, facet=None, category_path=None):
        return self.render_facet(request, segments, facet, category_path)

    def render_facet(self, request, segments, facet, category_path=None):
        C = request.environ['couchish']
        facets = [t for k, t in C.config.types.items() if k == 'facet_%s'%facet]
        if len(facets) == 1:
            return Facet(facets[0], category_path)


def category_form(C, facet, model_type, request):
    facet_definition = C.config.types['facet_%s'%facet]['fields']
    category_definition = C.config.types[model_type]['fields']
    for cat in category_definition:
        cat['name'] = 'category.*.new_category.%s'%cat['name']
    category_group = {'name': 'category.*.new_category', 'type': 'Structure'}
    checkbox = {'name': 'category.*.new_category.is_new','type': 'Boolean', 'widget': {'type': 'Checkbox'}}
    facet_definition.append( category_group )
    facet_definition.append( checkbox )
    defn = {'fields': facet_definition + category_definition }
    b = build(defn, C.db)
    b.renderer =  request.environ['restish.templating'].renderer
    return b
    

def filter_categories(facet, facet_path, category_path):
    out = []
    if category_path is None:
        depth = 0
    else:
        depth = len(category_path.split('.'))
    for c in facet['category']:
        if category_path is None or c['path'].startswith(category_path):
            cats = c['path'].split('.')
            if len(cats) == depth+1:
                c['_path'] = c['path']
                c['path'] = '.'.join(cats[depth:])
                out.append(c)
    return out



def create_category(S):

    def create(data):
        d = dict(data)
        d['model_type'] = 'category'
        return S.create(d)

    return create

def get_parent(cat):
    segments = cat.split('.')
    if len(segments) == 1:
        return ''
    else:
        return '.'.join(segments[:-1])

def build_tree(facet, root_url, category_path):
    ul_by_path = {}
    root = T.ul()
    ul_by_path[''] = root
    for c in facet['category']:
        u = T.ul()
        ul_by_path[c['path']] = u
        if c['path'] == category_path:
            class_ = 'selected'
        else:
            class_ = ''
        link = T.a(href=root_url.child(c['path']))[c['data']['label']]
        link.attrs['class'] = class_
        li_link = T.li()[link]
        parent = get_parent(c['path'])              
        ul_by_path[ parent ][ li_link, u ] 
    return flatten(root)

class Facet(BasePage):

    def __init__(self, facet, category_path):
        self.facet = facet
        self.path = self.facet['facet']['path']
        self.model_type = 'facet_%s'%self.path
        self.referenced_type = facet['facet']['model_type']
        self.category_path = category_path

    @resource.GET()
    def GET(self, request):
        return self.html(request)

    @resource.POST()
    def POST(self, request):
        C = request.environ['couchish']
        form = category_form(C, self.path, self.referenced_type)
        try:
            data = form.validate(request)
        except formish.FormError:
            return self.html(request, form)
        with C.session() as S:
            facet_docs = S.docs_by_type(self.model_type)
            facet_docs = list(facet_docs)
            assert len(facet_docs) == 1
            facet = list(facet_docs)[0]
            cats = categories.apply_changes(facet['category'], data['category'], self.path, self.category_path, create_category(S))
            facet['category'] = cats
        return http.see_other(request.url.path)

    @templating.page('/adminish/facet.html')
    def html(self, request, form=None):
        return self.render_page(request, form)

    def render_page(self, request, form):
        C = request.environ['couchish']
        form = category_form(C, self.path, self.referenced_type)
        with C.session() as S:
            facet_docs = S.docs_by_type(self.model_type)
        facet_docs = list(facet_docs)
        assert len(facet_docs) == 1
        facet = list(facet_docs)[0]
        root_url = url.URL('/admin/categories').child(self.path)
        tree = build_tree(facet, root_url, self.category_path)
        categories = filter_categories(facet, self.path, self.category_path)
        form.defaults = {'category': categories}
        return {'categories': categories, 'form':form, 'tree':tree, 'facet':self.facet}
        


class Page(BasePage):
    
    type = None
    label = None
    template = '/adminish/items.html'
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
            form.renderer =  request.environ['restish.templating'].renderer
            
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
            if isinstance(E, page.Element):
                E = util.RequestBoundCallable(E, request)
            return E
        data = {'form': form, 'items': items, 'pagingdata': pagingdata, 'metadata': M,'element':page_element, 'types':T, 'type':self.type} 
        return templating.render_response(request, self, M['templates']['items'], data)
    
    @resource.POST()
    def POST(self, request):
        C = request.environ['couchish']
        defn = C.config.types[self.type]
        form = build(defn, C.db)
        form.renderer =  request.environ['restish.templating'].renderer
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
    

class ItemPage(BasePage):
    
    type = None
    label = None
    template = '/adminish/item.html'
    
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
        form.renderer =  request.environ['restish.templating'].renderer
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
            if isinstance(E, page.Element):
                E = util.RequestBoundCallable(E, request)
            return E
        data = {'form': form, 'metadata': M,'element':page_element, 'type': self.type}
        return templating.render_response(request, self, M['templates']['item'], data)
            
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
        





