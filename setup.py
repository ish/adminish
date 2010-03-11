from setuptools import setup, find_packages

version = '0.1.3'

setup(name='adminish',
      version=version,
      description="Auto web admin system for couchdb and restish",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Tim Parkin & Matt Goodall',
      author_email='info@timparkin.co.uk',
      url='http://ish.io',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'restish',
          'formish',
          'adminish-categories',
          'couchish',
          'couchfti',
          'couchutil',
          'xappy',
          'wsgiapptools',
          'pagingish',
          'breve',
          'pastescript',
          'WebError',
          'repoze.who',
          'menuish',
          'notification',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [paste.app_factory]
      main = adminish.wsgiapp:make_app
      setupapp = adminish.websetup:setup_app
      [paste.app_install]
      main = paste.script.appinstall:Installer
      """,
      )
