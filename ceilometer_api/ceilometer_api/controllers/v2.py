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

from ceilometer.openstack.common import timeutils


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


class ResourcesController(RestController):
    """Works on resources."""

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

    resources = ResourcesController()


class ProjectsController(RestController):
    """Works on projects."""

    @expose('json')
    def _lookup(self, project_id, *remainder):
        return ProjectController(project_id), remainder


class SourceController(RestController):
    """Works on resources."""

    def __init__(self, source_id):
        request.context['source_id'] = source_id

    resources = ResourcesController()


class SourcesController(RestController):
    """Works on sources."""

    @expose('json')
    def _lookup(self, source_id, *remainder):
        return SourceController(source_id), remainder


class UserController(RestController):
    """Works on reusers."""

    def __init__(self, user_id):
        request.context['user_id'] = user_id

    resources = ResourcesController()


class UsersController(RestController):
    """Works on users."""

    @expose('json')
    def _lookup(self, user_id, *remainder):
        return UserController(user_id), remainder


class V2Controller(object):
    """Version 2 API controller root."""

    projects = ProjectsController()
    resources = ResourcesController()
    sources = SourcesController()
    users = UsersController()
