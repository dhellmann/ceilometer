# -*- encoding: utf-8 -*-
#
# Copyright © 2012 New Dream Network, LLC (DreamHost)
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

from pecan import make_app
from ceilometer_api import middleware
from ceilometer_api import model
from ceilometer_api import hooks
from ceilometer.service import prepare_service


def setup_app(config):

    model.init_model()

    # Initialize the cfg.CONF object
    prepare_service([])

    return make_app(
        config.app.root,
        static_root=config.app.static_root,
        template_path=config.app.template_path,
        logging=getattr(config, 'logging', {}),
        debug=getattr(config.app, 'debug', False),
        force_canonical=getattr(config.app, 'force_canonical', True),
        # FIXME: Replace DBHook with a hooks.TransactionHook
        hooks=[hooks.ConfigHook(), hooks.DBHook()],
        wrap_app=middleware.ParsableErrorMiddleware,
    )
