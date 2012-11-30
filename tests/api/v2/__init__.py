
from ceilometer.tests import api
from ceilometer.api.controllers import v2


class FunctionalTest(api.FunctionalTest):

    PATH_PREFIX = '/v2'

    def setUp(self):
        super(FunctionalTest, self).setUp()

    def tearDown(self):
        super(FunctionalTest, self).tearDown()
