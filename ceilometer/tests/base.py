#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright © 2012 New Dream Network (DreamHost)
#
# Author: Doug Hellmann <doug.hellmann@dreamhost.com>
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
"""Test base classes.
"""

import logging
import os
import unittest

import mox
import stubout

from ming import mim

from ceilometer.storage import impl_mongodb

LOG = logging.getLogger(__name__)

class TestConnection(impl_mongodb.Connection):

    _mim_instance = None
    FORCE_MONGO = bool(int(os.environ.get('CEILOMETER_TEST_LIVE', 0)))

    def _get_connection(self, conf):
        # Use a real MongoDB server if we can connect, but fall back
        # to a Mongo-in-memory connection if we cannot.
        if self.FORCE_MONGO:
            try:
                return super(Connection, self)._get_connection(conf)
            except:
                LOG.debug('Unable to connect to mongodb')
                raise
        else:
            LOG.debug('Using MIM for test connection')

            # MIM will die if we have too many connections, so use a
            # Singleton
            if TestConnection._mim_instance is None:
                LOG.debug('Creating a new MIM Connection object')
                TestConnection._mim_instance = mim.Connection()
            return TestConnection._mim_instance


class TestCase(unittest.TestCase):

    def setUp(self):
        super(TestCase, self).setUp()
        self.mox = mox.Mox()
        self.stubs = stubout.StubOutForTesting()

    def tearDown(self):
        self.mox.UnsetStubs()
        self.stubs.UnsetAll()
        self.stubs.SmartUnsetAll()
        self.mox.VerifyAll()
        super(TestCase, self).tearDown()
