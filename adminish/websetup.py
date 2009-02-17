"""Setup the infomy application"""
import logging

from adminish import wsgiapp

log = logging.getLogger(__name__)

MODEL_NAMES = ['page']

def setup_app(command, conf, vars):
    """Place any commands to setup infomy here"""


    # Create the store instance and sync the views.
    store = wsgiapp._make_couchish_store(conf)
    store.sync_views()


