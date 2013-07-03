# -*- encoding: utf-8 -*-
#
# Copyright © 2012 eNovance <licensing@enovance.com>
# Copyright © 2012 Red Hat, Inc
#
# Author: Julien Danjou <julien@danjou.info>
# Author: Eoghan Glynn <eglynn@redhat.com>
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

from ceilometer import counter
from ceilometer.compute import instance as compute_instance
from ceilometer.openstack.common import timeutils


def make_counter_from_instance(instance, name, type, unit, volume):
    return counter.Counter(
        name=name,
        type=type,
        unit=unit,
        volume=volume,
        user_id=instance.user_id,
        project_id=instance.tenant_id,
        resource_id=instance.id,
        timestamp=timeutils.isotime(),
        resource_metadata=compute_instance.get_metadata_from_object(instance),
    )


def instance_name(instance):
    """Shortcut to get instance name."""
    return getattr(instance, 'OS-EXT-SRV-ATTR:instance_name', None)
