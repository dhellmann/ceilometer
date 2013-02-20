# -*- encoding: utf-8 -*-
#
# Copyright © 2012-2013 eNovance <licensing@enovance.com>
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

from oslo.config import cfg

from ceilometer import agent
from ceilometer import extension_manager
from ceilometer import nova_client
from ceilometer.compute.virt import inspector as virt_inspector
from ceilometer.openstack.common import log


LOG = log.getLogger(__name__)


class AgentManager(agent.AgentManager):

    def __init__(self):
        super(AgentManager, self).__init__(
            extension_manager.ActivatedExtensionManager(
                namespace='ceilometer.poll.compute',
                disabled_names=cfg.CONF.disabled_compute_pollsters,
            ),
        )
        self._inspector = virt_inspector.get_hypervisor_inspector()

    def poll_instance(self, context, instance):
        """Poll one instance."""
        self.pollster_manager.map(self.publish_counters_from_one_pollster,
                                  manager=self,
                                  context=context,
                                  instance=instance)

    def periodic_tasks(self, context, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        nv = nova_client.Client()
        for instance in nv.instance_get_all_by_host(cfg.CONF.host):
            if getattr(instance, 'OS-EXT-STS:vm_state', None) != 'error':
                self.poll_instance(context, instance)

    @property
    def inspector(self):
        return self._inspector
