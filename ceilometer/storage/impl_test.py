"""In-memory storage driver for use with tests.

This driver is based on MIM, an in-memory version of MongoDB.
"""

import logging

from ming import mim

from ceilometer.storage import base
from ceilometer.storage import impl_mongodb


LOG = logging.getLogger(__name__)


class TestDBStorage(base.StorageEngine):
    """Put the data into an in-memory database for testing

    This driver is based on MIM, an in-memory version of MongoDB.

    Collections:

    - user
      - { _id: user id
          source: [ array of source ids reporting for the user ]
          }
    - project
      - { _id: project id
          source: [ array of source ids reporting for the project ]
          }
    - meter
      - the raw incoming data
    - resource
      - the metadata for resources
      - { _id: uuid of resource,
          metadata: metadata dictionaries
          timestamp: datetime of last update
          user_id: uuid
          project_id: uuid
          meter: [ array of {counter_name: string, counter_type: string} ]
        }
    """

    OPTIONS = []

    def register_opts(self, conf):
        """Register any configuration options used by this engine.
        """
        conf.register_opts(self.OPTIONS)

    def get_connection(self, conf):
        """Return a Connection instance based on the configuration settings.
        """
        return TestConnection(conf)


class TestConnection(impl_mongodb.Connection):

    _mim_instance = None

    def _get_connection(self, conf):
        # MIM will die if we have too many connections, so use a
        # Singleton
        if TestConnection._mim_instance is None:
            LOG.debug('Creating a new MIM Connection object')
            TestConnection._mim_instance = mim.Connection()
        return TestConnection._mim_instance
