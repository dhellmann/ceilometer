import os
from unittest import TestCase

from pecan import set_config
from pecan.testing import load_test_app

from ceilometer.openstack.common import cfg
from ceilometer import storage

__all__ = ['FunctionalTest']


class FunctionalTest(TestCase):
    """
    Used for functional tests where you need to test your
    literal application and its integration with the framework.
    """

    DBNAME = 'testdb'

    PATH_PREFIX = ''

    def setUp(self):

        cfg.CONF.database_connection = 'test://localhost/%s' % self.DBNAME
        self.conn = storage.get_connection(cfg.CONF)
        # Don't want to use drop_database() because we
        # may end up running out of spidermonkey instances.
        # http://davisp.lighthouseapp.com/projects/26898/tickets/22
        self.conn.conn[self.DBNAME].clear()

        # Determine where we are so we can set up paths in the config
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                '..',
                                                '..',
                                                )
                                   )
        self.config = {

            'app': {
                'root': 'ceilometer_api.controllers.root.RootController',
                'modules': ['ceilometer_api'],
                'static_root': '%s/public' % root_dir,
                'template_path': '%s/ceilometer_api/templates' % root_dir,
                'debug': True,
                'errors': {
                    404: '/error/404',
                    '__force_dict__': True
                    },
                },

            'logging': {
                'loggers': {
                    'root': {'level': 'INFO', 'handlers': ['console']},
                    'ceilometer_api': {'level': 'DEBUG',
                                       'handlers': ['console'],
                                       },
                    },
                'handlers': {
                    'console': {
                        'level': 'DEBUG',
                        'class': 'logging.StreamHandler',
                        'formatter': 'simple'
                        }
                    },
                'formatters': {
                    'simple': {
                        'format': ('%(asctime)s %(levelname)-5.5s [%(name)s]'
                                   '[%(threadName)s] %(message)s')
                        }
                    },
                },
            }

        self.app = load_test_app(self.config)

    def tearDown(self):
        set_config({}, overwrite=True)

    PATH_PREFIX = ''

    def get_json(self, path, **params):
        full_path = self.PATH_PREFIX + path
        #print 'GET: %s %r' % (full_path, params)
        return self.app.get(full_path, params=params).json
