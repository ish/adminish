import pkg_resources
import logging
import couchish, couchdb


log = logging.getLogger(__name__)


def make_adminish_config(types):
    allmetadata = {}
    for type, data in types.items():
        metadata = {}
        m = data.get('metadata',{})
        metadata['labels'] = m.get('labels',{})
        metadata['labels']['singular'] = m.get('labels',{}).get('singular', type.title())
        metadata['labels']['plural'] = m.get('labels',{}).get('plural', '%ss'%type.title())
        metadata['templates'] = m.get('templates',{})
        metadata['templates']['item'] = m.get('templates',{}).get('item', '/adminish/item.html')
        metadata['templates']['items'] = m.get('templates',{}).get('items','/adminish/items.html')
        metadata['pager'] = m.get('pager', 'CouchDBPaging')
        try:
            metadata['templates']['items-table'] = m.get('templates',{})['items-table']
            for n, entry in enumerate(metadata['templates']['items-table']):
                metadata['templates']['items-table'][n]['label'] = entry.get('label')
                metadata['templates']['items-table'][n]['value'] = entry.get('value')
        except KeyError:
            pass
        allmetadata[type] = metadata

    return allmetadata
            

def make_couchish_store(app_conf, model_resource):
    module, dir = model_resource.split('.',1)
    models={}
    for f in pkg_resources.resource_listdir(module, dir):
        if f.endswith('.model.yaml'):
            name, remaining = f.split('.',1)
            models[name] = pkg_resources.resource_filename(model_resource, f)
    views_file = pkg_resources.resource_filename(model_resource,'views.yaml')
    return couchish.CouchishStore(
        couchdb.Database(app_conf['couchish.db.url']),
        couchish.Config.from_yaml( models, views_file))




