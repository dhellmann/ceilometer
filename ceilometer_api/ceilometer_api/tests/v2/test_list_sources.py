# -*- encoding: utf-8 -*-
#
# Copyright © 2012 Julien Danjou
#
# Author: Julien Danjou <julien@danjou.info>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Test listing users.
"""

import mock

from ceilometer_api.tests.v2 import FunctionalTest


class TestListSource(FunctionalTest):

    TEST_DATA = {'test_source': {'somekey': 666}}
    LOAD_FUNC_NAME = 'ceilometer_api.controllers.v2.SourcesController._load_sources'

    def _get(self, path):
        with mock.patch(self.LOAD_FUNC_NAME) as m:
            m.return_value = self.TEST_DATA
            return self.get_json(path)

    def test_all(self):
        ydata = self._get('/sources')
        self.assert_('test_source' in ydata)

    def test_source(self):
        ydata = self._get('/sources/test_source')
        self.assert_("somekey" in ydata)
        self.assertEqual(ydata["somekey"], 666)

    def test_unknownsource(self):
        ydata = self._get('/sources/test_source_that_does_not_exist')
        self.assertEqual(ydata, {})
