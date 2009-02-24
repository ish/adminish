"""
WSGI/PasteDeploy application bootstrap module.
"""
import pkg_resources

import repoze.who.config
from wsgiapptools import cookies
from restish.app import RestishApp

from adminish.resource import root
from adminish.lib import templating, flash, admin

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
        environ['couchish'] = admin.make_couchish_store(app_conf)
        environ['adminish'] = admin.make_adminish_config(environ['couchish'].config.types)

        return app(environ, start_response)

    return application


