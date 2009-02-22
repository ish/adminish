#!/usr/bin/env python
from __future__ import with_statement
import couchdb
from optparse import OptionParser
import os
import yaml
from couchish import sync_categories

host = 'http://localhost:5984'

def sync(dbname, filename, update, remove_existing, verbose):
    S = couchdb.Server(host)
    if dbname not in S:
        raise ValueError("Database %r does not exist in %s"%(dbname, host))
    db = S[dbname]
    with open(filename, 'r') as f:
        categories = yaml.load(f)
    if verbose:
        print 'found %s root level category %r'%(len(categories), categories[0].keys())
    sync_categories.sync( db, categories, remove_existing=remove_existing, update=update, verbose=verbose )


def process(args, options):
    dbname = options.db
    filename = options.filename
    update = options.update
    remove_existing = options.remove_existing
    verbose = options.verbose
    sync(dbname, filename, update, remove_existing, verbose)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--db", action='store', dest="db", help="database name")
    parser.add_option("-f", "--filename", action='store', dest="filename", help="yaml category definition filename")
    parser.add_option("-u", "--update", action="store_true", dest="update", default=False, help="update existing data where possible")
    parser.add_option("-r", "--remove-existing", action="store_true", dest="remove_existing", default=False, help="remove all existing categories")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    (options, args) = parser.parse_args()
    if options.db is None:
        options.db = args[0]
    if options.verbose:
        print 'db = ',options.db
        print 'filename = ',options.filename
        print 'update = ',options.update
        print 'remove_existing = ',options.remove_existing
    process(args, options)

