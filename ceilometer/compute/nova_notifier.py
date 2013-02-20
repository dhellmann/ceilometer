# -*- encoding: utf-8 -*-
#
# Copyright © 2012 New Dream Network, LLC (DreamHost)
#
# Author: Julien Danjou <julien@danjou.info>
#         Doug Hellmann <doug.hellmann@dreamhost.com>
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

from nova import notifications
from nova.openstack.common.notifier import api as notifier_api

from oslo.config import cfg

from ceilometer.openstack.common import log as logging

from ceilometer import extension_manager
from ceilometer.compute.virt import inspector

try:
    from nova.conductor import api
    instance_info_source = api.API()
except ImportError:
    from nova import db as instance_info_source

# This module runs inside the nova compute
# agent, which only configures the "nova" logger.
# We use a fake logger name in that namespace
# so that messages from this module appear
# in the log file.
LOG = logging.getLogger('nova.ceilometer.notifier')

_gatherer = None


class DeletedInstanceStatsGatherer(object):

    def __init__(self, extensions):
        self.mgr = extensions
        self.inspector = inspector.get_hypervisor_inspector()

    def _get_counters_from_plugin(self, ext, instance, *args, **kwds):
        """Used with the extenaion manager map() method."""
        return ext.obj.get_counters(self, instance)

    def __call__(self, instance):
        counters = self.mgr.map(self._get_counters_from_plugin,
                                instance=instance,
                                )
        # counters is a list of lists, so flatten it before returning
        # the results
        results = []
        for clist in counters:
            results.extend(clist)
        return results


def initialize_gatherer(gatherer=None):
    """Set the callable used to gather stats for the instance.

    gatherer should be a callable accepting one argument (the instance
    ref), or None to have a default gatherer used
    """
    global _gatherer
    if gatherer is None:
        LOG.debug('making a new stats gatherer')
        mgr = extension_manager.ActivatedExtensionManager(
            namespace='ceilometer.poll.compute',
            disabled_names=cfg.CONF.disabled_compute_pollsters,
        )
        _gatherer = DeletedInstanceStatsGatherer(mgr)
    else:
        LOG.debug('using stats gatherer %r', gatherer)
        _gatherer = gatherer
    return _gatherer


def notify(context, message):
    if message['event_type'] != 'compute.instance.delete.start':
        return

    instance_id = message['payload']['instance_id']
    LOG.debug('polling final stats for %r', instance_id)

    gatherer = _gatherer or initialize_gatherer()
    instance = instance_info_source.instance_get_by_uuid(
        context,
        instance_id,
    )

    # Get the default notification payload
    payload = notifications.info_from_instance(
        context, instance, None, None)

    # Extend the payload with samples from our plugins.  We only need
    # to send some of the data from the counter objects, since a lot
    # of the fields are the same.
    counters = gatherer(instance)
    payload['samples'] = [{'name': c.name,
                           'type': c.type,
                           'unit': c.unit,
                           'volume': c.volume}
                          for c in counters]

    publisher_id = notifier_api.publisher_id('compute', None)

    # We could simply modify the incoming message payload, but we
    # can't be sure that this notifier will be called before the RPC
    # notifier. Modifying the content may also break the message
    # signature. So, we start a new message publishing. We will be
    # called again recursively as a result, but we ignore the event we
    # generate so it doesn't matter.
    notifier_api.notify(context, publisher_id,
                        'compute.instance.delete.samples',
                        notifier_api.INFO, payload)
