#!/usr/bin/env python
from jsonish import pythonjson as json
import couchdb
from optparse import OptionParser
import os

host = 'http://localhost:5984'

def create_items(dbname='test', num_items=50, force_create=False, verbose=False, model_type='test', items=None):

    S = couchdb.Server(host)
    if force_create == True and dbname in S:
        if verbose == True:
            print ' - deleting db %r'%dbname
        del S[dbname]
    if dbname not in S:
        if verbose == True:
            print 'creating db %r'%dbname
        db = S.create(dbname)
    else:
        db = S[dbname]
   
    if verbose == True:
        print 'creating items'
    if items is None:
        chars = 'abcdefghijklmnopqrst'
        for n in xrange(num_items):
            data = {'model_type':model_type,
                    'url':chars[n%10],
                    'title':chars[n%20].title()}
            if verbose == True:
                print ' %s - %r'%(n,data)
            db['%s'%n] = json.encode_to_dict(data)
    else:
        for n, item in enumerate(items):
            if verbose == True:
                print ' %s - %r'%(n,item)
            db[item['_id']] = json.encode_to_dict(item)
    return db



def process(args, options):
    dbname = options.db
    force_create = options.force_create
    model_type = options.model_type
    num_items = options.num_items
    verbose = options.verbose
    create_items(dbname, force_create, model_type, num_items, verbose)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--db", action='store', dest="db", help="database name", default='test')
    parser.add_option("-m", "--model-type", action='store', dest="model_type", help="model type to create", default='test')
    parser.add_option("-n", "--num-items", action='store', dest="num_items", type="int", help="number of items to create", default=50)
    parser.add_option("-f", "--force-create", action="store_true", dest="force_create", default=False, help="create a new database, deleting current if exists")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    (options, args) = parser.parse_args()
    if options.verbose:
        print 'db = ',options.db
        print 'model_type = ',options.model_type
        print 'num_items = ',options.num_items
        print 'force_create = ',options.force_create
    process(args, options)

