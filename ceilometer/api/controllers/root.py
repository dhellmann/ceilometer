from pecan import expose

from . import v2


class RootController(object):

    v2 = v2.V2Controller()

    @expose(generic=True, template='index.html')
    def index(self):
        # FIXME: Return version information
        return dict()
