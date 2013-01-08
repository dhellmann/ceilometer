# -*- encoding: utf-8 -*-
#
# Copyright © 2012 New Dream Network, LLC (DreamHost)
#
# Author: Doug Hellmann <doug.hellmann@dreamhost.com>
#         Angus Salkeld <asalkeld@redhat.com>
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
"""Version 2 of the API.
"""

# [GET ] / -- information about this version of the API
#
# [GET   ] /resources -- list the resources
# [GET   ] /resources/<resource> -- information about the resource
# [GET   ] /meters -- list the meters
# [POST  ] /meters -- insert a new sample (and meter/resource if needed)
# [GET   ] /meters/<meter> -- list the samples for this meter
# [PUT   ] /meters/<meter> -- update the meter (not the samples)
# [DELETE] /meters/<meter> -- delete the meter and samples
#
import datetime

import pecan
from pecan import request
from pecan.rest import RestController

import wsme
import wsme.pecan
from wsme.types import Base, text, Enum

from ceilometer.openstack.common import log as logging
from ceilometer.openstack.common import timeutils
from ceilometer import storage


LOG = logging.getLogger(__name__)


operation_kind = Enum(str, 'lt', 'le', 'eq', 'ne', 'ge', 'gt')


class Query(Base):
    field = text
    op = operation_kind
    value = text


def _query_to_kwargs(query):
    translatation = {'user_id': 'user',
                     'project_id': 'project',
                     'resource_id': 'resource',
                     'source': 'source'}
    kwargs = {}
    stamp = {}
    metaquery = {}
    for i in query:
        if i.field in translatation:
            kwargs[translatation[i.field]] = i.value
        elif i.field == 'timestamp' and i.op in ('lt', 'le'):
            stamp['end_timestamp'] = i.value
        elif i.field == 'timestamp' and i.op in ('gt', 'ge'):
            stamp['start_timestamp'] = i.value
        elif i.field == 'search_offset':
            stamp['search_offset'] = i.value
        elif i.field.startswith('metadata.'):
            metaquery[i.field] = i.value

    if len(metaquery) > 0:
        kwargs['metaquery'] = metaquery
    if len(stamp) > 0:
        kwargs.update(_get_query_timestamps(stamp))
    return kwargs


def _get_query_timestamps(args={}):
    """Return any optional timestamp information in the request.

    Determine the desired range, if any, from the GET arguments. Set
    up the query range using the specified offset.

    [query_start ... start_timestamp ... end_timestamp ... query_end]

    Returns a dictionary containing:

    query_start: First timestamp to use for query
    start_timestamp: start_timestamp parameter from request
    query_end: Final timestamp to use for query
    end_timestamp: end_timestamp parameter from request
    search_offset: search_offset parameter from request

    """
    search_offset = int(args.get('search_offset', 0))

    start_timestamp = args.get('start_timestamp')
    if start_timestamp:
        start_timestamp = timeutils.parse_isotime(start_timestamp)
        start_timestamp = start_timestamp.replace(tzinfo=None)
        query_start = (start_timestamp -
                       datetime.timedelta(minutes=search_offset))
    else:
        query_start = None

    end_timestamp = args.get('end_timestamp')
    if end_timestamp:
        end_timestamp = timeutils.parse_isotime(end_timestamp)
        end_timestamp = end_timestamp.replace(tzinfo=None)
        query_end = end_timestamp + datetime.timedelta(minutes=search_offset)
    else:
        query_end = None

    return {'query_start': query_start,
            'query_end': query_end,
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'search_offset': search_offset,
            }


def _flatten_metadata(metadata):
    """Return flattened resource metadata without nested structures
    and with all values converted to unicode strings.
    """
    return dict((k, unicode(v))
                for k, v in metadata.iteritems()
                if type(v) not in set([list, dict, set]))


class Sample(Base):
    source = text
    counter_name = text
    counter_type = text
    counter_volume = float
    user_id = text
    project_id = text
    resource_id = text
    timestamp = datetime.datetime
    resource_metadata = {text: text}
    message_id = text

    def __init__(self, counter_volume=None, resource_metadata={}, **kwds):
        if counter_volume is not None:
            counter_volume = float(counter_volume)
        resource_metadata = _flatten_metadata(resource_metadata)
        super(Sample, self).__init__(counter_volume=counter_volume,
                                    resource_metadata=resource_metadata,
                                    **kwds)


class Statistics(Base):
    min = float
    max = float
    avg = float
    sum = float
    count = int
    duration = float


class MeterController(RestController):
    """Manages operations on a single meter.
    """
    _custom_actions = {
        'statistics': ['GET'],
        }

    def __init__(self, meter_id):
        request.context['meter_id'] = meter_id
        self._id = meter_id

    @wsme.pecan.wsexpose([Sample], [Query])
    def get_all(self, q=[]):
        """Return all events for the meter.
        """
        kwargs = _query_to_kwargs(q)
        kwargs['meter'] = self._id
        print 'in get_all meter samples'
        print 'kwargs are: %s' % kwargs
        f = storage.EventFilter(**kwargs)
        return [Sample(**e)
            for e in request.storage_conn.get_raw_events(f)
            ]

    # TODO(jd) replace str for timestamp by datetime?
    @wsme.pecan.wsexpose(Statistics, [Query])
    def statistics(self, q=[]):
        """Computes the duration of the meter events in the time range given.
        """
        kwargs = _query_to_kwargs(q)
        kwargs['meter'] = self._id
        print 'in get_all meter statistics'
        print 'kwargs are: %s' % kwargs
        f = storage.EventFilter(**kwargs)
        stat = request.storage_conn.get_meter_statistics(f)
        return Statistics(**stat)


class Meter(Base):
    name = text
    type = text
    resource_id = text
    project_id = text
    user_id = text


class MetersController(RestController):
    """Works on meters."""

    @pecan.expose()
    def _lookup(self, meter_id, *remainder):
        return MeterController(meter_id), remainder

    @wsme.pecan.wsexpose([Meter], [Query])
    def get_all(self, q=[]):
        kwargs = _query_to_kwargs(q)
        print 'in get_all meters'
        print 'kwargs are: %s' % kwargs
        return [Meter(**m)
                for m in request.storage_conn.get_meters(**kwargs)]


class ResourceSummary(Base):
    resource_id = text
    project_id = text
    user_id = text
    source = text

    def __init__(self, **kwds):
        keys = ('resource_id', 'project_id', 'user_id', 'source')
        needed = dict((k, kwds.get(k)) for k in keys)
        super(ResourceSummary, self).__init__(**needed)


class Resource(Base):
    resource_id = text
    project_id = text
    user_id = text
    timestamp = datetime.datetime
    metadata = {text: text}

    def __init__(self, metadata={}, **kwds):
        metadata = _flatten_metadata(metadata)
        super(Resource, self).__init__(metadata=metadata, **kwds)


class ResourceController(RestController):
    """Manages operations on a single resource.
    """

    def __init__(self, resource_id):
        request.context['resource_id'] = resource_id

    @wsme.pecan.wsexpose([Resource])
    def get_all(self):
            r = request.storage_conn.get_resources(
                resource=request.context.get('resource_id'),
                )[0]
            return Resource(**r)


class ResourcesController(RestController):
    """Works on resources."""

    @pecan.expose()
    def _lookup(self, resource_id, *remainder):
        return ResourceController(resource_id), remainder

    @wsme.pecan.wsexpose([ResourceSummary], [Query])
    def get_all(self, q=[]):
        kwargs = _query_to_kwargs(q)
        print 'kwargs are: %s' % kwargs
        resources = [
            ResourceSummary(**r)
            for r in request.storage_conn.get_resources(**kwargs)]
        return resources


class V2Controller(object):
    """Version 2 API controller root."""

    resources = ResourcesController()
    meters = MetersController()
