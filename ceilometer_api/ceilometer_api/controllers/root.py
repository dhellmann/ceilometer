from pecan import expose, redirect
from webob.exc import status_map

from . import v2


class RootController(object):

    v2 = v2.V2Controller()

    @expose(generic=True, template='index.html')
    def index(self):
        # FIXME: Return version information
        return dict()

    # FIXME: Remove
    @index.when(method='POST')
    def index_post(self, q):
        redirect('http://pecan.readthedocs.org/en/latest/search.html?q=%s' % q)

    # FIXME: Remove
    @expose('error.html')
    def error(self, status):
        try:
            status = int(status)
        except ValueError:  # pragma: no cover
            status = 500
        message = getattr(status_map.get(status), 'explanation', '')
        return dict(status=status, message=message)
