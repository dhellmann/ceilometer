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
import inspect
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

    _op = None

    def get_op(self):
        return self._op or 'eq'

    def set_op(self, value):
        self._op = value

    field = text
    "The name of the field to test"

    op = wsme.wsproperty(operation_kind, get_op, set_op)
    "The comparison operator"

    value = text
    "The value to compare against the field values"

    def __repr__(self):
        # for logging calls
        return '<Query %r %s %r>' % (self.field, self.op, self.value)

    @classmethod
    def sample(cls):
        return cls(field='resource_id',
                   op='eq',
                   value='d99c8ace-dce8-4f25-8677-2004d363280b',
                   )


def _query_to_kwargs(query, db_func):
    # TODO(dhellmann): This function needs tests of its own.
    valid_keys = inspect.getargspec(db_func)[0]
    if 'self' in valid_keys:
        valid_keys.remove('self')
    translatation = {'user_id': 'user',
                     'project_id': 'project',
                     'resource_id': 'resource'}
    stamp = {}
    trans = {}
    metaquery = {}
    for i in query:
        LOG.debug('_query_to_kwargs i=%s', i)
        if i.field == 'timestamp':
            # FIXME(dhellmann): This logic is not consistent with the
            # way the timestamps are treated inside the mongo driver
            # (the end timestamp is always tested using $lt). We
            # should just pass a single timestamp through to the
            # storage layer with the operator and let the storage
            # layer use that operator.
            if i.op in ('lt', 'le'):
                stamp['end_timestamp'] = i.value
            elif i.op in ('gt', 'ge'):
                stamp['start_timestamp'] = i.value
            else:
                LOG.warn('_query_to_kwargs ignoring %r unexpected op %r"' %
                         (i.field, i.op))
        else:
            if i.op != 'eq':
                LOG.warn('_query_to_kwargs ignoring %r unimplemented op %r' %
                         (i.field, i.op))
            elif i.field == 'search_offset':
                stamp['search_offset'] = i.value
            elif i.field.startswith('metadata.'):
                metaquery[i.field] = i.value
            else:
                trans[translatation.get(i.field, i.field)] = i.value

    kwargs = {}
    if metaquery and 'metaquery' in valid_keys:
        kwargs['metaquery'] = metaquery
    if stamp:
        q_ts = _get_query_timestamps(stamp)
        if 'start' in valid_keys:
            kwargs['start'] = q_ts['query_start']
            kwargs['end'] = q_ts['query_end']
        elif 'start_timestamp' in valid_keys:
            kwargs['start_timestamp'] = q_ts['query_start']
            kwargs['end_timestamp'] = q_ts['query_end']
        else:
            raise wsme.exc.UnknownArgument('timestamp', "not valid for this resource")

    if trans:
        for k in trans:
            if k not in valid_keys:
                raise wsme.exc.UnknownArgument(i.field, "unrecognized query field")
            kwargs[k] = trans[k]

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
    duration_start = datetime.datetime
    duration_end = datetime.datetime

    def __init__(self, start_timestamp=None, end_timestamp=None, **kwds):
        super(Statistics, self).__init__(**kwds)
        LOG.debug('Statistics start_timestamp %s', start_timestamp)
        LOG.debug('Statistics end_timestamp %s', end_timestamp)
        LOG.debug('Statistics %s', kwds)
        self._update_duration(start_timestamp, end_timestamp)

    def _update_duration(self, start_timestamp, end_timestamp):
        # "Clamp" the timestamps we return to the original time
        # range, excluding the offset.
        if (start_timestamp and
                self.duration_start and
                self.duration_start < start_timestamp):
            self.duration_start = start_timestamp
            LOG.debug('clamping min timestamp to range')
        if (end_timestamp and
                self.duration_end and
                self.duration_end > end_timestamp):
            self.duration_end = end_timestamp
            LOG.debug('clamping max timestamp to range')

        # If we got valid timestamps back, compute a duration in minutes.
        #
        # If the min > max after clamping then we know the
        # timestamps on the events fell outside of the time
        # range we care about for the query, so treat them as
        # "invalid."
        #
        # If the timestamps are invalid, return None as a
        # sentinal indicating that there is something "funny"
        # about the range.
        if self.duration_start and self.duration_end and \
          (self.duration_start <= self.duration_end):
            # Can't use timedelta.total_seconds() because
            # it is not available in Python 2.6.
            diff = self.duration_end - self.duration_start
            self.duration = (diff.seconds + (diff.days * 24 * 60 ** 2)) / 60
        else:
            self.duration_start = self.duration_end = self.duration = None


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
        kwargs = _query_to_kwargs(q, storage.EventFilter.__init__)
        kwargs['meter'] = self._id
        f = storage.EventFilter(**kwargs)
        return [Sample(**e)
                for e in request.storage_conn.get_raw_events(f)
                ]

    @wsme.pecan.wsexpose(Statistics, [Query])
    def statistics(self, q=[]):
        """Computes the statistics of the meter events in the time range given.
        """
        kwargs = _query_to_kwargs(q, storage.EventFilter.__init__)
        kwargs['meter'] = self._id
        LOG.debug('MeterController.statistics %s', kwargs)
        f = storage.EventFilter(**kwargs)
        computed = request.storage_conn.get_meter_statistics(f)
        # Find the original timestamp in the query to use for clamping
        # the duration returned in the statistics.
        start = end = None
        for i in q:
            if i.field == 'timestamp' and i.op in ('lt', 'le'):
                end = timeutils.parse_isotime(i.value).replace(tzinfo=None)
            elif i.field == 'timestamp' and i.op in ('gt', 'ge'):
                start = timeutils.parse_isotime(i.value).replace(tzinfo=None)
        stat = Statistics(start_timestamp=start,
                          end_timestamp=end,
                          **computed)
        return stat


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
        kwargs = _query_to_kwargs(q, request.storage_conn.get_meters)
        return [Meter(**m)
                for m in request.storage_conn.get_meters(**kwargs)]


class Resource(Base):
    """Something for which metering data was collected.
    """

    resource_id = text
    "The UUID of the resource"

    project_id = text
    "The owner of the resource"

    user_id = text
    "The user who created or modified the resource"

    timestamp = datetime.datetime
    "The last time a sample for any meter related to the resource was seen"

    metadata = {text: text}
    "Information about the resource"

    def __init__(self, metadata={}, **kwds):
        metadata = _flatten_metadata(metadata)
        super(Resource, self).__init__(metadata=metadata, **kwds)

    @classmethod
    def sample(cls):
        return cls(resource_id='d99c8ace-dce8-4f25-8677-2004d363280b',
                   project_id='c59244c9-bdee-4088-8666-6c0e8b6f2680',
                   user_id='045d63ed-f190-4066-ab6f-6ca53b2dfb0d',
                   timestamp=datetime.datetime(2013, 1, 11, 16, 49),
                   metadata={'field': 'value',
                             'another_field': 2,
                             })


class ResourceController(RestController):
    """Manages operations on a single resource.
    """

    def __init__(self, resource_id):
        request.context['resource_id'] = resource_id

    @wsme.pecan.wsexpose([Resource])
    def get_all(self):
            r = request.storage_conn.get_resources(
                resource=request.context.get('resource_id'))[0]
            return Resource(**r)


class ResourcesController(RestController):
    """Works on resources."""

    @pecan.expose()
    def _lookup(self, resource_id, *remainder):
        return ResourceController(resource_id), remainder

    @wsme.pecan.wsexpose([Resource], [Query])
    def get_all(self, q=[]):
        kwargs = _query_to_kwargs(q, request.storage_conn.get_resources)
        LOG.debug('ResourcesController.get_all kwargs=%s', kwargs)
        resources = [
            Resource(**r)
            for r in request.storage_conn.get_resources(**kwargs)]
        return resources


class V2Controller(object):
    """Version 2 API controller root."""

    resources = ResourcesController()
    meters = MetersController()
