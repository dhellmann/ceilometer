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
"""Version 2 of the API.
"""

# [ ] / -- information about this version of the API
#
# [ ] /extensions -- list of available extensions
# [ ] /extensions/<extension> -- details about a specific extension
#
# [ ] /sources -- list of known sources (where do we get this?)
# [ ] /sources/components -- list of components which provide metering
#                            data (where do we get this)?
#
# [x] /projects/<project>/resources -- list of resource ids
# [x] /resources -- list of resource ids
# [x] /sources/<source>/resources -- list of resource ids
# [x] /users/<user>/resources -- list of resource ids
#
# [x] /users -- list of user ids
# [x] /sources/<source>/users -- list of user ids
#
# [x] /projects -- list of project ids
# [x] /sources/<source>/projects -- list of project ids
#
# [ ] /resources/<resource> -- metadata
#
# [ ] /projects/<project>/meters -- list of meters reporting for parent obj
# [ ] /resources/<resource>/meters -- list of meters reporting for parent obj
# [ ] /sources/<source>/meters -- list of meters reporting for parent obj
# [ ] /users/<user>/meters -- list of meters reporting for parent obj
#
# [x] /projects/<project>/meters/<meter> -- events
# [x] /resources/<resource>/meters/<meter> -- events
# [x] /sources/<source>/meters/<meter> -- events
# [x] /users/<user>/meters/<meter> -- events
#
# [ ] /projects/<project>/meters/<meter>/duration -- total time for selected
#                                                    meter
# [x] /resources/<resource>/meters/<meter>/duration -- total time for selected
#                                                      meter
# [ ] /sources/<source>/meters/<meter>/duration -- total time for selected
#                                                  meter
# [ ] /users/<user>/meters/<meter>/duration -- total time for selected meter
#
# [ ] /projects/<project>/meters/<meter>/volume -- total or max volume for
#                                                  selected meter
# [x] /projects/<project>/meters/<meter>/volume/max -- max volume for
#                                                      selected meter
# [x] /projects/<project>/meters/<meter>/volume/sum -- total volume for
#                                                      selected meter
# [ ] /resources/<resource>/meters/<meter>/volume -- total or max volume for
#                                                    selected meter
# [x] /resources/<resource>/meters/<meter>/volume/max -- max volume for
#                                                        selected meter
# [x] /resources/<resource>/meters/<meter>/volume/sum -- total volume for
#                                                        selected meter
# [ ] /sources/<source>/meters/<meter>/volume -- total or max volume for
#                                                selected meter
# [ ] /users/<user>/meters/<meter>/volume -- total or max volume for selected
#                                            meter

import datetime
import os

import pecan
from pecan import request
from pecan.rest import RestController

import wsme
import wsme.pecan
from wsme.types import Base, text, wsattr

from ceilometer.openstack.common import jsonutils
from ceilometer.openstack.common import log as logging
from ceilometer.openstack.common import timeutils
from ceilometer import storage


LOG = logging.getLogger(__name__)


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


# FIXME(dhellmann): Change APIs that use this to return float?
class MeterVolume(Base):
    """Response type for queries that summarize meter data.
    """

    volume = wsattr(float, mandatory=False)
    "The summarized meter volume."

    def __init__(self, volume, **kw):
        if volume is not None:
            volume = float(volume)
        super(MeterVolume, self).__init__(volume=volume, **kw)

    @staticmethod
    def sample():
        return MeterVolume(1.2)


class MeterVolumeController(object):

    @wsme.pecan.wsexpose(MeterVolume)
    def max(self):
        """Find the maximum volume for the matching meter events.
        """
        q_ts = _get_query_timestamps(request.params)

        try:
            meter = request.context['meter_id']
        except KeyError:
            raise ValueError('No meter specified')

        resource = request.context.get('resource_id')
        project = request.context.get('project_id')

        # Query the database for the max volume
        f = storage.EventFilter(meter=meter,
                                resource=resource,
                                start=q_ts['query_start'],
                                end=q_ts['query_end'],
                                project=project,
                                )

        # TODO(sberler): do we want to return an error if the resource
        # does not exist?
        results = list(request.storage_conn.get_volume_max(f))

        value = None
        if results:
            if resource:
                # If the caller specified a resource there should only
                # be one result.
                value = results[0].get('value')
            else:
                # FIXME(sberler): Currently get_volume_max is really
                # always grouping by resource_id.  We should add a new
                # function in the storage driver that does not do this
                # grouping (and potentially rename the existing one to
                # get_volume_max_by_resource())
                value = max(result.get('value') for result in results)

        return MeterVolume(volume=value)

    @wsme.pecan.wsexpose(MeterVolume)
    def sum(self):
        """Compute the total volume for the matching meter events.
        """
        q_ts = _get_query_timestamps(request.params)

        try:
            meter = request.context['meter_id']
        except KeyError:
            raise ValueError('No meter specified')

        resource = request.context.get('resource_id')
        project = request.context.get('project_id')

        f = storage.EventFilter(meter=meter,
                                project=project,
                                start=q_ts['query_start'],
                                end=q_ts['query_end'],
                                resource=resource,
                                )

        # TODO(sberler): do we want to return an error if the resource
        # does not exist?
        results = list(request.storage_conn.get_volume_sum(f))

        value = None
        if results:
            if resource:
                # If the caller specified a resource there should only
                # be one result.
                value = results[0].get('value')
            else:
                # FIXME(sberler): Currently get_volume_max is really
                # always grouping by resource_id.  We should add a new
                # function in the storage driver that does not do this
                # grouping (and potentially rename the existing one to
                # get_volume_max_by_resource())
                value = sum(result.get('value') for result in results)

        return MeterVolume(volume=value)


class Event(Base):
    """A single recorded sample of data about a meter and resource.
    """

    source = text
    "The name of the source for identities. See :type:`Source`."

    counter_name = text
    "The name of the thing being measured. See :ref:`measurements`."

    counter_type = text
    "The style of measurement taken. See :ref:`measurements`."

    counter_volume = float
    "The recorded measurement."

    user_id = text
    "The identity of the user consuming the resource, if known."

    project_id = text
    "The identity of the project that owns the resource."

    resource_id = text
    "The id of the thing against which the measurement was taken."

    timestamp = datetime.datetime
    "The date and time when the measurement was taken."

    # FIXME(dhellmann): Need to add the metadata back as
    # a flat {text: text} mapping.
    #resource_metadata = ?

    message_id = text
    "A unique identifier for the measurement."

    def __init__(self, counter_volume=None, **kwds):
        if counter_volume is not None:
            counter_volume = float(counter_volume)
        super(Event, self).__init__(counter_volume=counter_volume,
                                    **kwds)

    @staticmethod
    def sample():
        return Event(source='openstack',
                     counter_name='vcpus',
                     counter_type='gauge',
                     counter_volume=2.0,
                     user_id='29dc1ab009814c0dbb172a61710566d2',
                     project_id='a68b6a458fa844deb00fee665e647a83',
                     resource_id='297c82316e8445b7b8f15ae87ebcebdd',
                     timestamp=datetime.datetime(2012, 4, 16, 8, 0, 0),
                     message_id='dd9a0612712e4fe192e18a33eff4e302',
                     )


class Duration(Base):
    """Response type for the duration query for a meter.
    """

    start_timestamp = datetime.datetime
    """
    The earliest time stamp for which data is known. If
    ``search_offset`` is used, this may be the start timestamp from
    the original query if there is an earlier event that falls within
    the offset.
    """

    end_timestamp = datetime.datetime
    """
    The latest time stamp for which data is known. If
    ``search_offset`` is used, this may be the end timestamp from the
    original query if there is a later event that falls within the
    offset.
    """

    duration = float
    """The difference between end_timestamp and start_timestamp in
    seconds.
    """

    @staticmethod
    def sample():
        ""
        return Duration(start_timestamp=datetime.datetime(2012, 12, 5, 12, 10),
                        end_timestamp=datetime.datetime(2012, 12, 5, 13, 10),
                        duration=60 * 60,
                        )


class MeterController(RestController):
    """Manages operations on a single meter.
    """

    volume = MeterVolumeController()

    _custom_actions = {
        'duration': ['GET'],
        }

    def __init__(self, meter_id):
        request.context['meter_id'] = meter_id
        self._id = meter_id

    @wsme.pecan.wsexpose([Event])
    def get_all(self):
        """Return all events for the meter.
        """
        q_ts = _get_query_timestamps(request.params)
        f = storage.EventFilter(
            user=request.context.get('user_id'),
            project=request.context.get('project_id'),
            start=q_ts['query_start'],
            end=q_ts['query_end'],
            resource=request.context.get('resource_id'),
            meter=self._id,
            source=request.context.get('source_id'),
            )
        return [Event(**e)
                for e in request.storage_conn.get_raw_events(f)
                ]

    @wsme.pecan.wsexpose(Duration)
    def duration(self):
        """Computes the duration of the meter events in the time range given.
        """
        q_ts = _get_query_timestamps(request.params)
        start_timestamp = q_ts['start_timestamp']
        end_timestamp = q_ts['end_timestamp']

        # Query the database for the interval of timestamps
        # within the desired range.
        f = storage.EventFilter(user=request.context.get('user_id'),
                                project=request.context.get('project_id'),
                                start=q_ts['query_start'],
                                end=q_ts['query_end'],
                                resource=request.context.get('resource_id'),
                                meter=self._id,
                                source=request.context.get('source_id'),
                                )
        min_ts, max_ts = request.storage_conn.get_event_interval(f)

        # "Clamp" the timestamps we return to the original time
        # range, excluding the offset.
        LOG.debug('start_timestamp %s, end_timestamp %s, min_ts %s, max_ts %s',
                  start_timestamp, end_timestamp, min_ts, max_ts)
        if start_timestamp and min_ts and min_ts < start_timestamp:
            min_ts = start_timestamp
            LOG.debug('clamping min timestamp to range')
        if end_timestamp and max_ts and max_ts > end_timestamp:
            max_ts = end_timestamp
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
        if min_ts and max_ts and (min_ts <= max_ts):
            # Can't use timedelta.total_seconds() because
            # it is not available in Python 2.6.
            diff = max_ts - min_ts
            duration = (diff.seconds + (diff.days * 24 * 60 ** 2)) / 60
        else:
            min_ts = max_ts = duration = None

        return Duration(start_timestamp=min_ts,
                        end_timestamp=max_ts,
                        duration=duration,
                        )


class Meter(Base):
    """Describes the measurement being taken.

    See :ref:`measurements` for a complete list.
    """

    name = text
    "The unique name of the meter."

    type = text
    "One of cumulative, guage, or delta."

    resource_id = text
    "UUID of the resource for which the meter is collected."

    project_id = text
    "UUID of the project for which the meter is collected."

    user_id = text
    "UUID of the user for which the meter is collected."

    @staticmethod
    def sample():
        return Meter(name='instance',
                     type='gauge',
                     user_id='29dc1ab009814c0dbb172a61710566d2',
                     project_id='a68b6a458fa844deb00fee665e647a83',
                     resource_id='297c82316e8445b7b8f15ae87ebcebdd',
                     )


class MetersController(RestController):
    """Works on meters."""

    @pecan.expose()
    def _lookup(self, meter_id, *remainder):
        return MeterController(meter_id), remainder

    @wsme.pecan.wsexpose([Meter])
    def get_all(self):
        user_id = request.context.get('user_id')
        project_id = request.context.get('project_id')
        resource_id = request.context.get('resource_id')
        source_id = request.context.get('source_id')
        return [Meter(**m)
                for m in request.storage_conn.get_meters(user=user_id,
                                                         project=project_id,
                                                         resource=resource_id,
                                                         source=source_id,
                                                         )]


class ResourceController(RestController):
    """Manages operations on a single resource.
    """

    def __init__(self, resource_id):
        request.context['resource_id'] = resource_id

    meters = MetersController()


class MeterDescription(Base):
    """Describes a measurement being taken.

    See :ref:`measurements` for a complete list.
    """

    counter_name = text
    "The name of the measurement."

    counter_type = text
    "One of cumulative, gauge, or delta."


class Resource(Base):
    """An object for which measurements can be taken.

    For example, instances, networks, images, etc.
    """

    resource_id = text
    "UUID of the resource"

    project_id = text
    "owner of the resource"

    user_id = text
    "user triggering resource use"

    timestamp = datetime.datetime
    "the last time a measurement for this resource was taken"

    #metadata = ?

    meter = wsattr([MeterDescription])
    "a list of the names of meters collecting data for this resource"

    def __init__(self, meter=[], **kwds):
        meter = [MeterDescription(**m) for m in meter]
        super(Resource, self).__init__(meter=meter, **kwds)


class ResourcesController(RestController):
    """Works on resources."""

    @pecan.expose()
    def _lookup(self, resource_id, *remainder):
        return ResourceController(resource_id), remainder

    @wsme.pecan.wsexpose([Resource])
    def get_all(self, start_timestamp=None, end_timestamp=None):
        if start_timestamp:
            start_timestamp = timeutils.parse_isotime(start_timestamp)
        if end_timestamp:
            end_timestamp = timeutils.parse_isotime(end_timestamp)

        resources = [
            Resource(**r)
            for r in request.storage_conn.get_resources(
                source=request.context.get('source_id'),
                user=request.context.get('user_id'),
                project=request.context.get('project_id'),
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                )]
        return resources


class ProjectController(RestController):
    """Works on resources."""

    def __init__(self, project_id):
        request.context['project_id'] = project_id

    meters = MetersController()
    resources = ResourcesController()


class ProjectsController(RestController):
    """Works on projects."""

    @pecan.expose()
    def _lookup(self, project_id, *remainder):
        return ProjectController(project_id), remainder

    @wsme.pecan.wsexpose([text])
    def get_all(self):
        source_id = request.context.get('source_id')
        projects = list(request.storage_conn.get_projects(source=source_id))
        return projects

    meters = MetersController()


class UserController(RestController):
    """Works on reusers."""

    def __init__(self, user_id):
        request.context['user_id'] = user_id

    meters = MetersController()
    resources = ResourcesController()


class UsersController(RestController):
    """Works on users."""

    @pecan.expose()
    def _lookup(self, user_id, *remainder):
        return UserController(user_id), remainder

    @wsme.pecan.wsexpose([text])
    def get_all(self):
        source_id = request.context.get('source_id')
        users = list(request.storage_conn.get_users(source=source_id))
        return users


class Source(Base):
    """Definition of an identity source.

    A source defines the scope of the project and user identifiers in
    a meter.  Different sources can be registered through a
    configuration file, and their details retrieved through the API to
    map resource usage to billable customers.
    """

    name = text
    """
    The unique name of the source. This must be the same in the source
    configuration file and in the metering event data.
    """

    data = wsattr({text: text})
    """
    Arbitrary key/value pairs of data from the source configuration
    file. This can include any data useful for integrators working on
    a given deployment.
    """

    @staticmethod
    def sample():
        return Source(name='openstack',
                      data={'key': 'value'})


class SourceController(RestController):
    """Works on resources."""

    def __init__(self, source_id, data):
        request.context['source_id'] = source_id
        self._id = source_id
        self._data = data

    @wsme.pecan.wsexpose(Source)
    def get(self):
        response = Source(name=self._id, data=self._data)
        return response

    meters = MetersController()
    resources = ResourcesController()
    projects = ProjectsController()
    users = UsersController()


class SourcesController(RestController):
    """Works on sources."""

    def __init__(self):
        self._sources = None

    @property
    def sources(self):
        # FIXME(dhellmann): Add a configuration option for the filename.
        #
        # FIXME(dhellmann): We only want to load the file once in a process,
        # but we want to be able to mock the loading out in separate tests.
        #
        if not self._sources:
            self._sources = self._load_sources(os.path.abspath("sources.json"))
        return self._sources

    @staticmethod
    def _load_sources(filename):
        try:
            with open(filename, "r") as f:
                sources = jsonutils.load(f)
        except IOError as err:
            LOG.warning('Could not load data source definitions from %s: %s' %
                        (filename, err))
            sources = {}
        return sources

    @pecan.expose()
    def _lookup(self, source_id, *remainder):
        try:
            data = self.sources[source_id]
        except KeyError:
            # Unknown source
            pecan.abort(404, detail='No source %s' % source_id)
        return SourceController(source_id, data), remainder

    @wsme.pecan.wsexpose([Source])
    def get_all(self):
        return [Source(name=key, data=value)
                for key, value in self.sources.iteritems()]


class V2Controller(object):
    """Version 2 API controller root."""

    projects = ProjectsController()
    resources = ResourcesController()
    sources = SourcesController()
    users = UsersController()
    meters = MetersController()
