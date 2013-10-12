#!/usr/bin/python
#
# Copyright (c) 2013 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Test the ability to convert files into wsgi generators
"""

import os
import os.path
import types
from wsgiref.util import setup_testing_defaults

from os_loganalyze.tests import base
import os_loganalyze.wsgi as log_wsgi


SEVS = {
    'NONE': 0,
    'DEBUG': 1,
    'INFO': 2,
    'AUDIT': 3,
    'TRACE': 4,
    'WARNING': 5,
    'ERROR': 6
    }

SEVS_SEQ = ['NONE', 'DEBUG', 'INFO', 'AUDIT', 'TRACE', 'WARNING', 'ERROR']


def _start_response(*args):
    return


def fake_env(**kwargs):
    environ = dict(**kwargs)
    setup_testing_defaults(environ)
    print environ
    return environ


def samples_path():
    """Create an abs path for our test samples

    Because the wsgi has a security check that ensures that we don't
    escape our root path, we need to actually create a full abs path
    for the tests, otherwise the sample files aren't findable.
    """
    return os.path.join(os.getcwd(), 'os_loganalyze/tests/samples/')


class TestWsgiBasic(base.TestCase):

    def test_invalid_file(self):
        gen = log_wsgi.application(fake_env(), _start_response)
        self.assertEqual(gen, ['Invalid file url'])

    def test_file_not_found(self):
        gen = log_wsgi.application(fake_env(PATH_INFO='/htmlify/foo.txt'),
                                   _start_response)
        self.assertEqual(gen, ['File Not Found'])

    def test_found_file(self):
        gen = log_wsgi.application(
            fake_env(PATH_INFO='/htmlify/screen-c-api.txt.gz'),
            _start_response, root_path=samples_path())
        self.assertEqual(type(gen), types.GeneratorType)

    def test_plain_text(self):
        gen = log_wsgi.application(
            fake_env(PATH_INFO='/htmlify/screen-c-api.txt.gz'),
            _start_response, root_path=samples_path())

        first = gen.next()
        self.assertIn(
            '+ ln -sf /opt/stack/new/screen-logs/screen-c-api.2013-09-27-1815',
            first)

    def test_html_gen(self):
        gen = log_wsgi.application(
            fake_env(
                PATH_INFO='/htmlify/screen-c-api.txt.gz',
                HTTP_ACCEPT='text/html'
                ),
            _start_response, root_path=samples_path())

        first = gen.next()
        self.assertIn('<html>', first)


class TestKnownFiles(base.TestCase):
    files = {
        'screen-c-api.txt.gz': {
            'TOTAL': 3695,
            'DEBUG': 2906,
            'INFO': 486,
            'AUDIT': 249,
            'TRACE': 0,
            'WARNING': 50,
            'ERROR': 0,
            },
        'screen-key.txt.gz': {
            'TOTAL': 144983
            },
        'screen-n-api.txt.gz': {
            'TOTAL': 50745,
            'DEBUG': 46071,
            'INFO': 4388,
            'AUDIT': 271,
            'TRACE': 0,
            'WARNING': 6,
            'ERROR': 5
            },
        'screen-q-svc.txt.gz': {
            'TOTAL': 47887,
            'DEBUG': 46912,
            'INFO': 262,
            'AUDIT': 0,
            'TRACE': 589,
            'WARNING': 48,
            'ERROR': 72,
            }
        }

    def count_types(self, gen):
        counts = {
            'TOTAL': 0,
            'DEBUG': 0,
            'INFO': 0,
            'WARNING': 0,
            'ERROR': 0,
            'TRACE': 0,
            'AUDIT': 0}

        laststatus = None
        for line in gen:
            counts['TOTAL'] = counts['TOTAL'] + 1
            for key in counts:
                if ' %s ' % key in line:
                    laststatus = key
                    continue
            if laststatus:
                counts[laststatus] = counts[laststatus] + 1
        return counts

    def compute_total(self, level, fname):
        # todo, be more clever
        counts = self.files[fname]
        total = 0
        for l in SEVS_SEQ[SEVS[level]:]:
            # so that we don't need to know all the levels
            if counts.get(l):
                total = total + counts[l]
        return total

    def test_pass_through_all(self):
        for fname in self.files:
            gen = log_wsgi.application(
                fake_env(
                    PATH_INFO='/htmlify/%s' % fname,
                    ),
                _start_response, root_path=samples_path())

            counts = self.count_types(gen)
            self.assertEqual(counts['TOTAL'], self.files[fname]['TOTAL'])

    def test_pass_through_at_levels(self):
        for fname in self.files:
            for level in self.files[fname]:
                if level == 'TOTAL':
                    continue

                gen = log_wsgi.application(
                    fake_env(
                        PATH_INFO='/htmlify/%s' % fname,
                        QUERY_STRING='level=%s' % level
                        ),
                    _start_response, root_path=samples_path())

                counts = self.count_types(gen)
                total = self.compute_total(level, fname)
                print fname, counts

                self.assertEqual(counts['TOTAL'], total)
