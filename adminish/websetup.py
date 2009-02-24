import logging

from adminish.lib import admin

log = logging.getLogger(__name__)

def setup_app(command, conf, vars):
    store = admin.make_couchish_store(conf)
    store.sync_views()


