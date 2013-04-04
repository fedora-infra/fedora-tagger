#!/usr/bin/python

__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

from fedoratagger import APP
from fedoratagger.lib import model

session = model.create_tables(APP.config['DB_URL'], debug=True)

import sys

if '--with-dev-data' in sys.argv:
    package = model.Package(id=1, name="mattd", summary="Matt Daemon")
    session.add(package)
    session.commit()
