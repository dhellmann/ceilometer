from pecan import hooks

from ceilometer.openstack.common import cfg
from ceilometer import storage


class ConfigHook(hooks.PecanHook):
    """Attach the configuration object to the request
    so controllers can get to it.
    """

    def before(self, state):
        state.request.cfg = cfg.CONF


class DBHook(hooks.PecanHook):

    def before(self, state):
        storage_engine = storage.get_engine(state.request.cfg)
        state.request.storage_engine = storage_engine
        state.request.storage_conn = storage_engine.get_connection(
            state.request.cfg)

    # def after(self, state):
    #     print 'method:', state.request.method
    #     print 'response:', state.response.status
