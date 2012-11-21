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
import logging
import os

from pecan import expose, request
from pecan.rest import RestController

from ceilometer.openstack.common import jsonutils
from ceilometer.openstack.common import timeutils
from ceilometer import storage


LOG = logging.getLogger(__name__)


def _list_events(meter,
                 project=None,
                 start=None,
                 end=None,
                 resource=None,
                 source=None,
                 user=None):
    """Return a list of raw metering events.
    """
    f = storage.EventFilter(user=user,
                            project=project,
                            start=start,
                            end=end,
                            source=source,
                            meter=meter,
                            resource=resource,
                            )
    return list(request.storage_conn.get_raw_events(f))


def _list_resources(source=None, user=None, project=None,
                    start_timestamp=None, end_timestamp=None):
    """Return a list of resource identifiers.
    """
    if start_timestamp:
        start_timestamp = timeutils.parse_isotime(start_timestamp)
    if end_timestamp:
        end_timestamp = timeutils.parse_isotime(end_timestamp)
    return list(request.storage_conn.get_resources(
            source=source,
            user=user,
            project=project,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            ))


def _list_projects(source=None):
    """Return a list of project names.
    """
    projects = request.storage_conn.get_projects(source=source)
    return list(projects)


def _list_users(source=None):
    """Return a list of user names.
    """
    users = request.storage_conn.get_users(source=source)
    return list(users)


def _get_query_timestamps(args={}):
    # Determine the desired range, if any, from the
    # GET arguments. Set up the query range using
    # the specified offset.
    # [query_start ... start_timestamp ... end_timestamp ... query_end]
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

    return dict(query_start=query_start,
                query_end=query_end,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                search_offset=search_offset,
                )


class MeterController(RestController):

    _custom_actions = {
        'duration': ['GET'],
        }

    def __init__(self, meter_id):
        request.context['meter_id'] = meter_id
        self._id = meter_id

    @expose('json')
    def get_all(self):
        """Return all events for the meter.
        """
        q_ts = _get_query_timestamps(request.params)
        events = _list_events(user=request.context.get('user_id'),
                              project=request.context.get('project_id'),
                              start=q_ts['query_start'],
                              end=q_ts['query_end'],
                              resource=request.context.get('resource_id'),
                              meter=self._id,
                              source=request.context.get('source_id'),
                              )
        return {'events': events}

    @expose('json')
    def duration(self):
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

        return {'start_timestamp': min_ts,
                'end_timestamp': max_ts,
                'duration': duration,
                }


class MetersController(RestController):
    """Works on meters."""

    @expose()
    def _lookup(self, meter_id, *remainder):
        return MeterController(meter_id), remainder


class ResourceController(RestController):

    def __init__(self, resource_id):
        request.context['resource_id'] = resource_id

    meters = MetersController()


class ResourcesController(RestController):
    """Works on resources."""

    @expose()
    def _lookup(self, resource_id, *remainder):
        return ResourceController(resource_id), remainder

    @expose('json')
    def get_all(self, start_timestamp=None, end_timestamp=None):
        project_id = request.context.get('project_id')
        source_id = request.context.get('source_id')
        user_id = request.context.get('user_id')
        return {'resources': _list_resources(project=project_id,
                                             source=source_id,
                                             user=user_id,
                                             start_timestamp=start_timestamp,
                                             end_timestamp=end_timestamp,
                                             ),
                }


class ProjectController(RestController):
    """Works on resources."""

    def __init__(self, project_id):
        request.context['project_id'] = project_id

    meters = MetersController()
    resources = ResourcesController()


class ProjectsController(RestController):
    """Works on projects."""

    @expose()
    def _lookup(self, project_id, *remainder):
        return ProjectController(project_id), remainder

    @expose('json')
    def get_all(self):
        source_id = request.context.get('source_id')
        return {'projects': _list_projects(source=source_id),
                }

    meters = MetersController()


class UserController(RestController):
    """Works on reusers."""

    def __init__(self, user_id):
        request.context['user_id'] = user_id

    meters = MetersController()
    resources = ResourcesController()


class UsersController(RestController):
    """Works on users."""

    @expose()
    def _lookup(self, user_id, *remainder):
        return UserController(user_id), remainder

    @expose('json')
    def get_all(self):
        source_id = request.context.get('source_id')
        return {'users': _list_users(source=source_id),
                }


class SourceController(RestController):
    """Works on resources."""

    def __init__(self, source_id, data):
        request.context['source_id'] = source_id
        self._id = source_id
        self._data = data

    @expose('json')
    def get(self):
        return self._data

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

    @expose()
    def _lookup(self, source_id, *remainder):
        return (SourceController(source_id, self.sources.get(source_id, {})),
                remainder)

    @expose('json')
    def get_all(self):
        return self.sources


class V2Controller(object):
    """Version 2 API controller root."""

    projects = ProjectsController()
    resources = ResourcesController()
    sources = SourcesController()
    users = UsersController()
