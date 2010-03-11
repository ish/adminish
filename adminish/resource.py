from __future__ import with_statement
import logging
from restish import resource, http, util, templating, page
import formish, schemaish, validatish
from restish import url
from wsgiapptools import flash

from couchish.couchish_formish_jsonbuilder import build, WidgetRegistry
from adminish import md
import adminishcategories as categories

from pagingish import webpaging

from breve.tags.html import tags as T
from breve.flatten import flatten

log = logging.getLogger(__name__)

from dottedish import api, dottedlist, dotteddict, set as _set
from couchdbsession import a8n

api.wrap.when_type(a8n.List)(dottedlist.wrap_list)
api.setitem.when_type(a8n.List)(dottedlist.setitem_list)
api.getitem.when_type(a8n.List)(dottedlist.getitem_list)

api.wrap.when_type(a8n.Dictionary)(dotteddict.wrap_dict)
api.setitem.when_type(a8n.Dictionary)(dotteddict.setitem_dict)
api.getitem.when_type(a8n.Dictionary)(dotteddict.getitem_dict)



#
# Pager factory configuration.
#
def get_views(view_args, model_type):
    """
    Lookup the 'all' and 'all_count' views from the metadata or construct
    defaults.
    """
    # XXX Why pop?
    metadata = view_args.pop('metadata')
    all_view = metadata.get('views', {}).get('all')
    if not all_view:
        all_view= '%s/all'%model_type
    all_count_view = metadata.get('views', {}).get('all_count')
    if not all_count_view:
        all_count_view= '%s/all_count'%model_type
    return all_view, all_count_view

def make_Pager(request, session, model_type, **view_args):
    all_view, all_count_view = get_views(view_args, model_type)
    return webpaging.paged_view(request, session, all_view, view_args)

def make_SkipLimitPager(request, session, model_type, **view_args):
    all_view, all_count_view = get_views(view_args, model_type)
    return webpaging.paged_skiplimit_view(request, session, all_view, all_count_view, view_args)

PAGER_FACTORIES = {'Paging': make_Pager,
                   'SkipLimitPaging': make_SkipLimitPager}


def make_form(request, *args, **kwargs):
    kwargs['renderer'] = request.environ['restish.templating'].renderer
    return formish.Form(*args, **kwargs)

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
        raise http.BadRequestError('incorrect id')
    if src['_rev'] != dest['_rev']:
        raise http.ConflictError([('Content-Type', 'text/plain')], 'rev is out of date')


class Markdown(BasePage):

    @resource.POST()
    @templating.page('/adminish/preview.html')
    def GET(self, request):
        return {'data':md.md(request.POST.get('data',''))}


class Admin(BasePage):
    
    @resource.GET()
    @templating.page('/adminish/root.html')
    def GET(self, request):
        model_metadata =  request.environ['adminish']['types']
        return {'model_metadata':model_metadata}

    @resource.child('_markdown')
    def markdown(self, request, segments):
        return Markdown()

    @resource.child()
    def categories(self, request, segments):
        return Categories()

    @resource.child('{type}')
    def items(self, request, segments, type=None):
        return ItemsPage(type=type)

    @resource.child('{type}/{id}')
    def item(self, request, segments, type=None, id=None):
        return ItemPage(id, type=type)

    @resource.child('{type}/_new')
    def new_item(self, request, segments, type=None, id=None):
        return NewItemPage(id, type=type)


class Categories(BasePage):

    @resource.GET()
    def GET(self, request):
        return self.html(request)

    @templating.page('/adminish/facets.html')
    def html(self, request, form=None):
        C = _store(request)
        facets = dict([(t['facet']['path'],t) for k, t in C.config.types.items() if k.startswith('facet_')])
        return {'facets': facets}

    @resource.child('{facet}')
    def facet(self, request, segments, facet=None):
        return self.render_facet(request, segments, facet)

    @resource.child('{facet}/{category_path}')
    def facet_categories(self, request, segments, facet=None, category_path=None):
        return self.render_facet(request, segments, facet, category_path)

    def render_facet(self, request, segments, facet, category_path=None):
        C = _store(request)
        facets = [t for k, t in C.config.types.items() if k == 'facet_%s'%facet]
        if len(facets) == 1:
            return Facet(facets[0], category_path)


def category_form(C, facet, model_type, request):
    # Take copies of the facet and category definitios so we can modify them
    # without affecting the core config.
    facet_definition = list(C.config.types['facet_%s'%facet]['fields'])
    category_definition = [dict(i) for i in C.config.types[model_type]['fields']]
    for cat in category_definition:
        cat['name'] = 'category.*.new_category.%s'%cat['name']
    category_group = {'name': 'category.*.new_category', 'type': 'Structure'}
    checkbox = {'name': 'category.*.new_category.is_new','type': 'Boolean', 'widget': {'type': 'Checkbox'}}
    facet_definition.append( category_group )
    facet_definition.append( checkbox )
    defn = {'fields': facet_definition + category_definition }
    b = build(defn, C, widget_registry=_widget_registry(request))
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
    cats = list(facet['category'])
    cats.sort(lambda x, y: cmp(len(x['path'].split('.')), len(y['path'].split('.'))))
    for c in cats:
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
        # facet is the facet dict where category_path is the key string
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
        C = _store(request)
        type_config = C.config.types[self.model_type]
        form = category_form(C, self.path, self.referenced_type, request)
        try:
            data = form.validate(request)
        except formish.FormError:
            return self.html(request, form)
        with C.session() as S:
            facet_docs = S.docs_by_type(self.model_type)
            facet_docs = list(facet_docs)
            assert len(facet_docs) == 1
            facet = list(facet_docs)[0]
            # facet is the couch document for 'facet_%s'%path where the docs has a key 'category'
            # which is a list of dicts =
            # [{'path': 'scotland.argyll', 
            #   'data': ref_to_category whose keys= 'keywords','model_type','_ref','label',
            #   'id': couchuuid},]
            cats, changelog = categories.apply_changes(facet['category'], data['category'], self.category_path, create_category(S))
            view = type_config.get('metadata', {}).get('categorypath-rev')
            if view is None:
                view = '%s/categorypath-rev'%self.model_type
            for old,new in changelog:
                items = list(S.view(view,include_docs=True,startkey=old, endkey=old))
                for item in items:
                    _set(item.doc, item.value, new)
            # Get the results of the view that matches each change
            facet['category'] = cats
        return http.see_other(request.url.path)

    @templating.page('/adminish/facet.html')
    def html(self, request, form=None):
        return self.render_page(request, form)

    def render_page(self, request, form):
        C = _store(request)
        form = category_form(C, self.path, self.referenced_type, request)
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

def make_search_form(request):
    s = schemaish.Structure()
    s.add('q', schemaish.String())
    f = formish.Form(s, name="search", method="GET")
    return f



class ItemsPage(BasePage):
    
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
    def html(self, request):
        C = _store(request)
        defn = C.config.types[self.type]
        form = _form_for_type(request, C, defn)
        return self.render_page(request, form)

    def render_page(self, request, form):
        config = _config(request)
        C = _store(request)
        M = config['types'][self.type]
        T = C.config.types[self.type]

        searchform = make_search_form(request)
        if not formish.form_in_request(request) == searchform.name:
            q = None
        else:
            data = searchform.validate(request)
            q = data['q']

        pager = PAGER_FACTORIES[M['pager']]
        if q:
            searcher = request.environ['searcher']
            pagingdata = webpaging.paged_search(request, searcher, self.type, q, max_pagesize=10)
            keys = [item.id for item in pagingdata['items']]
            with C.session() as S:
                results = S.docs_by_type(self.type, keys=keys)
            items = results
        else:
            pagingdata = pager(request, C.session(), self.type, include_docs=True, metadata=M)
            items = [item.doc for item in pagingdata['items']]





        def page_element(name):
            E = self.element(request, name)
            if isinstance(E, page.Element):
                E = util.RequestBoundCallable(E, request)
            return E
        data = {'form': form, 'items': items, 'pagingdata': webpaging.Paging(request, pagingdata), 'metadata': M,'element':page_element, 'types':T, 'type':self.type, 'searchform': searchform} 
        return templating.render_response(request, self, M['templates']['items'], data)
    
    @resource.POST()
    def POST(self, request):
        C = _store(request)
        defn = C.config.types[self.type]
        form = _form_for_type(request, C, defn)
        try:
            data = form.validate(request)
        except formish.FormError:
            return self.render_page(request, form)
        with C.session() as S:
            S.create(_doc_create(self.type, data))
        flash.add_message(request.environ, 'item created.', 'success')
        return http.see_other(request.url)
    
    def resource_child(self, request, segments):
        return self.item_resource(segments[0]), segments[1:]
    

class NewItemPage(BasePage):
    
    type = None
    label = None
    template = '/adminish/new_item.html'
    
    def __init__(self, id, type=None, label=None, template=None):
        self.id = id
        if type is not None:
            self.type = type
        if label is not None:
            self.label = label
        if template is not None:
            self.template = template

    @resource.GET()
    def html(self, request):
        return self._html(request)

    @resource.POST()
    def post(self, request):
        C = _store(request)
        defn = C.config.types[self.type]
        form = _form_for_type(request, C, defn)
        try:
            data = form.validate(request)
        except formish.FormError:
            return self._html(request, form)
        C = _store(request)
        with C.session() as S:
            S.create(_doc_create(self.type, data))
        flash.add_message(request.environ, 'item created.', 'success')
        came_from = request.GET.get('came_from')
        if came_from:
            return http.see_other(request.application_url+came_from)
        return http.see_other(request.url.parent())

    def _html(self, request, form=None):
        if form is None:
            C = _store(request)
            defn = C.config.types[self.type]
            form = _form_for_type(request, C, defn)
        M = request.environ['adminish']['types'][self.type]
        return templating.render_response(
            request, self, M['templates']['new_item'],
            {'metadata': M, 'form': form})


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
        C = _store(request)
        defn = C.config.types[self.type]
        allowed_fields = request.GET.get('allowed',None)
        if allowed_fields is not None:
            allowed = allowed_fields.split(',')
            fields = []
            C = _store(request)
            defn = C.config.types[self.type]
            for field in defn['fields']:
                for prefix in allowed:
                    if field['key'].startswith(prefix):
                        fields.append(field)
                        break
            # Copy dict before altering it to avoid changing it permanently.
            defn = dict(defn)
            defn['fields'] = fields
        form = _form_for_type(request, C, defn, add_id_and_rev=True)
        form._actions = []
        form.action_url = request.url.path_qs
        form.add_action('submit','Submit',self.update_item)
        form.add_action('delete','Delete',self.delete_item)
        return form

    @resource.GET()
    def html(self, request, form=None):
        C = _store(request)
        if form is None:
            form = self.get_form(request)
            with C.session() as S:
                form.defaults = S.doc_by_id(self.id)
        return self.render_page(request, form)
        
    def render_page(self, request, form):
        M = request.environ['adminish']['types'][self.type]
        template_override = request.GET.get('template',None)
        if template_override == 'bare':
            template = '/adminish/bare.html'
        else:
            template = M['templates']['item']
        def page_element(name):
            E = self.element(request, name)
            if isinstance(E, page.Element):
                E = util.RequestBoundCallable(E, request)
            return E
        data = {'form': form, 'metadata': M,'element':page_element, 'type': self.type}
        return templating.render_response(request, self, template, data)
            
    @resource.POST()
    def POST(self, request):
        form = self.get_form(request)      
        return form.action(request)

    def delete_item(self, request, form):
        C = _store(request)
        with C.session() as S:
            doc = S.doc_by_id(self.id)
            S.delete(doc)
        flash.add_message(request.environ, 'item deleted.', 'success')
        return http.see_other(request.url.parent())
    
    def update_item(self, request, form):
        C = _store(request)
        try:
            data = form.validate(request)
        except formish.FormError:
            return self.render_page(request, form)
        with C.session() as S:
            doc = S.doc_by_id(self.id)
            # XXX Capture the error and display a useful page.
            confirm_doc_and_rev(doc, data)
            doc.update(data)
        flash.add_message(request.environ, 'item updated.', 'success')
        came_from = request.GET.get('came_from')
        if came_from:
            return http.see_other(request.application_url+came_from)
        return http.see_other(request.url.parent())


###
# Helper functions
#

def _form_for_type(request, C, defn, add_id_and_rev=False):
    """
    Create a form for the given model type.
    """
    form = build(defn, C, add_id_and_rev=add_id_and_rev,
                 widget_registry=_widget_registry(request))
    form.renderer =  request.environ['restish.templating'].renderer
    return form


def _doc_create(type, data):
    """
    Create a new doc from the model type and form data.
    """
    doc = dict(data)
    doc.update({'model_type': type})
    return doc


###
# Configuration.


def _config(request):
    """
    Retrieve the adminish config from the request.
    """
    return request.environ['adminish']


def _store(request):
    """
    Get the couchish store from the config.
    """
    return _config(request)['store_factory'](request)


def _widget_registry(request):
    """
    Create a widget registry from the config, defaulting to couchish's default.
    """
    factory = _config(request).get('widget_registry_factory') or WidgetRegistry
    return factory(_store(request))

