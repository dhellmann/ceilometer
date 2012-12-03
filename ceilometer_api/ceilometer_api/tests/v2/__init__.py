import mox
import stubout

from ceilometer_api import tests
from ceilometer_api.controllers import v2


class FunctionalTest(tests.FunctionalTest):

    PATH_PREFIX = '/v2'

    SOURCE_DATA = {'test_source': {'somekey': '666'}}

    def setUp(self):
        super(FunctionalTest, self).setUp()
        self.mox = mox.Mox()
        self.stubs = stubout.StubOutForTesting()
        self._stubout_sources()

    def _stubout_sources(self):
        """Source data is usually read from a file, but
        we want to let tests define their own. The class
        attribute SOURCE_DATA is injected into the controller
        as though it was read from the usual configuration
        file.
        """
        self.stubs.SmartSet(v2.SourcesController, 'sources',
                            self.SOURCE_DATA)

    def tearDown(self):
        self.mox.UnsetStubs()
        self.stubs.UnsetAll()
        self.stubs.SmartUnsetAll()
        self.mox.VerifyAll()
        super(FunctionalTest, self).tearDown()
