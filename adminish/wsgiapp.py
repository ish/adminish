"""
WSGI/PasteDeploy application bootstrap module.
"""
import pkg_resources
import couchish, couchdb

import repoze.who.config
from wsgiapptools import cookies
from adminish.lib import templating, flash

from restish.app import RestishApp

from adminish.resource import root





MODEL_NAMES = ['page']

def make_app(global_conf, **app_conf):
    """
    PasteDeploy WSGI application factory.

    Called by PasteDeply (or a compatable WSGI application host) to create the
    adminish WSGI application.
    """
    
    app = RestishApp(root.Root())
    app = repoze.who.config.make_middleware_with_config(app, global_conf, app_conf['repoze.who.ini'])
    app = setup_environ(app, global_conf, app_conf)
    # General "middleware".
    app = flash.flash_middleware_factory(app)
    app = cookies.cookies_middleware_factory(app)
    return app


def setup_environ(app, global_conf, app_conf):
    """
    WSGI application wrapper factory for extending the WSGI environ with
    application-specific keys.
    """

    # Create any objects that should exist for the lifetime of the application
    # here. Don't forget to actually include them in the environ below!
    renderer = templating.make_renderer(app_conf)

    def application(environ, start_response):

        # Add additional keys to the environ here.
        environ['restish.templating.renderer'] = renderer
        environ['couchish'] = _make_couchish_store(app_conf)
        environ['adminish'] = _make_adminish_config(environ['couchish'].config.types)

        return app(environ, start_response)

    return application


def _make_adminish_config(types):
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
            

def _make_couchish_store(app_conf):
    return couchish.CouchishStore(
        couchdb.Database(app_conf['couchish.db.url']),
        couchish.Config.from_yaml(
            dict((name,_model_filename(name)) for name in MODEL_NAMES),
            _couchish_config_filename('views.yaml')))


def _model_filename(model_name):
    return _couchish_config_filename('%s.yaml'%model_name)


def _couchish_config_filename(filename):
    return pkg_resources.resource_filename('adminish.model', filename)


