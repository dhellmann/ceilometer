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
"""Sphinx extension for automatically generating documentation for API.
"""
import inspect
import pprint

from docutils.parsers.rst import directives

from pecan.rest import RestController

from sphinx.ext import autodoc

import wsme.sphinxext


class ControllerDocumenter(autodoc.ClassDocumenter):
    domain = 'wsme'
    objtype = 'controller'
    directivetype = 'service'
    priority = 100

    option_spec = dict(
        autodoc.ClassDocumenter.option_spec,
        **{'webpath': directives.unchanged,
           })

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        print 'CAN DOCUMENT:', member
        return isinstance(member, RestController)

    def add_directive_header(self, sig):
        super(ControllerDocumenter, self).add_directive_header(sig)
        # remove the :module: option that was added by ClassDocumenter
        if ':module:' in self.directive.result[-1]:
            self.directive.result.pop()

    def format_signature(self):
        return u''

    def format_name(self):
        # if 'webpath' in self.options:
        #     return self.options['webpath']
        if '::' in self.name:
            obj_name = self.name.split('::')[-1]
            obj_path = obj_name.split('.')
            obj_path[0] = ''  # replace root controller name with empty string
            return '/'.join(obj_path)
        else:
            return '/' + self.options.webpath

    def document_members(self, all_members=False):
        print 'ControllerDocumenter.document_members', all_members
        return super(ControllerDocumenter, self).document_members(True)

    # def _get_members(self, o):

    def filter_members(self, members, want_all):
        pprint.pprint(members)
        self.options.undoc_members = True
        filtered = super(ControllerDocumenter, self).filter_members(members, want_all)
        pprint.pprint(filtered)
        return filtered

    # def get_object_members(self, want_all):
    #     print 'ControllerDocumenter.get_object_members', want_all
    #     resp = super(ControllerDocumenter, self).get_object_members(want_all)
    #     members_check_module, members = resp
    #     pprint.pprint(members)
    #     members = [(n, v) for n, v in members
    #                if inspect.ismethod(v) or isinstance(v, RestController)]
    #     pprint.pprint(members)
    #     return (members_check_module, members)


def setup(app):
    # app.add_autodocumenter(ControllerDocumenter)
    pass
    
