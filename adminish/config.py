import pkg_resources
import logging
import couchish


log = logging.getLogger(__name__)


def make_adminish_config(couchish_config, store_factory):
    """
    Build a configuration dict for adminish.

    :param: couchish_config the couchish config instance
    :param: store_factory func with signature store_factory(request) that will
            return the couchish store for the current request.
    """
    config = {'store_factory': store_factory,
              'types': {}}
    for type, data in couchish_config.types.items():
        # Copy the couchish metadata so we don't affect it.
        metadata = dict(data.get('metadata', {}))
        # Enhance the metadata for adminish.
        # Labels ...
        labels = metadata.setdefault('labels', {})
        if 'singular' not in labels:
            labels['singular'] = type.title()
        if 'plural' not in labels:
            labels['plural'] = type.title() + 's'
        # Paging ...
        metadata.setdefault('pager', 'Paging')
        # Templates ...
        templates = metadata.setdefault('templates', {})
        if 'item' not in templates:
            templates['item'] = '/adminish/item.html'
        if 'new_item' not in templates:
            templates['new_item'] = '/adminish/new_item.html'
        if 'items' not in templates:
            templates['items'] = '/adminish/items.html'
        items_table = templates.get('items-table', [])
        for n, entry in enumerate(items_table):
            items_table[n]['label'] = entry.get('label')
            items_table[n]['value'] = entry.get('value')
        # Add to full set.
        config['types'][type] = metadata
    return config
            

def make_couchish_config(app_conf, model_resource):
    module, dir = model_resource.split('.',1)
    models={}
    for f in pkg_resources.resource_listdir(module, dir):
        if f.endswith('.model.yaml'):
            name, remaining = f.split('.',1)
            models[name] = pkg_resources.resource_filename(model_resource, f)
    views_file = pkg_resources.resource_filename(model_resource,'views.yaml')
    return couchish.Config.from_yaml( models, views_file)

