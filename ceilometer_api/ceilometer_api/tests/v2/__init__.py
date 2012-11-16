import mox
import stubout

from ceilometer_api import tests


class FunctionalTest(tests.FunctionalTest):

    PATH_PREFIX = '/v2'

    def setUp(self):
        super(FunctionalTest, self).setUp()
        self.mox = mox.Mox()
        self.stubs = stubout.StubOutForTesting()

    def tearDown(self):
        self.mox.UnsetStubs()
        self.stubs.UnsetAll()
        self.stubs.SmartUnsetAll()
        self.mox.VerifyAll()
        super(FunctionalTest, self).tearDown()
