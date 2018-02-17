""" Prometheus Registration client reactive charm layer

This file is part of Prometheus Registration client reactive charm layer.
Copyright 2016 Canonical Ltd.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License version 3, as published by the
Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranties of MERCHANTABILITY,
SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from copy import copy
import json
import mock
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import charms.promreg


class TestPromRegReq(unittest.TestCase):

    def setUp(self):
        self.req_types = ["DELETE", "GET", "POST", "PUT"]
        self.config = {"promreg_url": "http://127.0.0.1:12321", "promreg_authtoken": "abc"}

        patched_hookenv_config = mock.patch('charmhelpers.core.hookenv.config', return_value=self.config)
        patched_hookenv_config.start()

        patched_hookenv_log = mock.patch('charmhelpers.core.hookenv.log')
        self.hookenv_log = patched_hookenv_log.start()

        self.requests = {}
        for rtype in self.req_types:
            patched_requests = mock.patch('requests.' + rtype.lower())
            self.requests[rtype] = patched_requests.start()

    def tearDown(self):
        mock.patch.stopall()

    def testNoURL(self):
        """ Verify a log entry, no error and no request if the promreg_url is not set.
        """
        self.config["promreg_url"] = ''
        for rtype in self.req_types:
            ret = charms.promreg.promreg_req(rtype, '', {})
            self.assertIsNone(ret)
            self.requests[rtype].assert_not_called()

        self.assertEqual(len(self.hookenv_log.call_args_list), len(self.req_types))

    def testBasic(self):
        """ Verify a basic requests call for each request type.
        """
        url = self.config['promreg_url'] + '/targets/'
        headers = {'AuthToken': self.config['promreg_authtoken']}
        for rtype in self.req_types:
            charms.promreg.promreg_req(rtype, '', {})
            if rtype == "GET":
                self.requests[rtype].assert_called_with(url=url, headers=headers)
            else:
                self.requests[rtype].assert_called_with(url=url, headers=headers, data='{}')


class TestRegister(unittest.TestCase):

    def setUp(self):
        self.host = "127.0.1.1"
        self.port = 9103
        self.req_types = ["DELETE", "GET", "POST", "PUT"]
        self.config = {"promreg_url": "http://127.0.0.1:12321", "promreg_authtoken": "abc"}
        os.environ['JUJU_UNIT_NAME'] = 'test_juju_unit'
        self.url = self.config['promreg_url'] + '/targets/' + '{}:{}'.format(self.host, self.port)
        self.headers = {'AuthToken': self.config['promreg_authtoken']}

        patched_hookenv_charm_name = mock.patch('charmhelpers.core.hookenv.charm_name', return_value='test_charm')
        patched_hookenv_charm_name.start()

        patched_hookenv_config = mock.patch('charmhelpers.core.hookenv.config', return_value=self.config)
        patched_hookenv_config.start()

        execution_environment = {'env': {'JUJU_ENV_NAME': 'test_juju_env'}}
        patched_hookenv_execution_enviroment = mock.patch('charmhelpers.core.hookenv.execution_environment',
                                                          return_value=execution_environment)
        patched_hookenv_execution_enviroment.start()

        patched_hookenv_log = mock.patch('charmhelpers.core.hookenv.log')
        self.hookenv_log = patched_hookenv_log.start()

        self.requests = {}
        for rtype in self.req_types:
            patched_requests = mock.patch('requests.' + rtype.lower())
            self.requests[rtype] = patched_requests.start()

        self.default_labels = charms.promreg.get_default_labels()  # must be after the mocked data

        self.exists = mock.MagicMock()
        self.exists.status_code = 200
        self.exists.labels = {"labelname1": "labelvalue1"}
        self.exists.labels.update(self.default_labels)
        json_mock = mock.MagicMock(return_value=[{"Host": "127.0.0.1", "labels": self.exists.labels}])
        self.exists.json = json_mock
        self.exists.text = json.dumps([{"Host": "127.0.0.1", "labels": self.exists.labels}])

    def tearDown(self):
        mock.patch.stopall()

    def testNoURL(self):
        """ Verify no url and only a log entry if no promreg_url is set.
        """
        self.config["promreg_url"] = ''
        charms.promreg.register(self.host, self.port, None)

        for rtype in self.req_types:
            self.requests[rtype].assert_not_called()
        self.assertEqual(len(self.hookenv_log.call_args_list), 1)

    def testNew(self):
        self.exists.text = 'null'
        self.requests['GET'].return_value = self.exists
        self.requests['POST'].return_value = self.exists  # For post just the status_code is needed

        labels = self.default_labels
        labels["labelname1"] = "labelvalue1"
        body = {'comment': 'Added by charm test_charm', 'labels': labels}

        # try with port being a string or an int both should work
        charms.promreg.register(self.host, self.port, labels)
        called_kwargs = self.requests['POST'].call_args[1]
        self.assertEqual(called_kwargs.get('url'), self.url)
        self.assertEqual(called_kwargs.get('headers'), self.headers)
        self.assertEqual(json.loads(called_kwargs.get('data')), body)

        # test with no labels and string for the port
        del labels['labelname1']
        charms.promreg.register(self.host, str(self.port), None)
        called_kwargs = self.requests['POST'].call_args[1]
        self.assertEqual(called_kwargs.get('url'), self.url)
        self.assertEqual(called_kwargs.get('headers'), self.headers)
        self.assertEqual(json.loads(called_kwargs.get('data')), body)

        self.requests['PUT'].assert_not_called()
        self.requests['DELETE'].assert_not_called()

    def testNoChange(self):
        self.requests['GET'].return_value = self.exists
        charms.promreg.register(self.host, self.port, self.exists.labels)

        self.requests['POST'].assert_not_called()
        self.requests['PUT'].assert_not_called()
        self.requests['DELETE'].assert_not_called()

    def testUpdate(self):
        self.requests['GET'].return_value = self.exists
        self.requests['PUT'].return_value = self.exists  # For put just the status_code is needed
        labels = copy(self.exists.labels)
        labels["labelname2"] = "labelvalue2"

        charms.promreg.register(self.host, self.port, labels)

        body = {'comment': 'Added by charm test_charm', 'labels': labels}
        called_kwargs = self.requests['PUT'].call_args[1]
        self.assertEqual(called_kwargs.get('url'), self.url)
        self.assertEqual(called_kwargs.get('headers'), self.headers)
        self.assertEqual(json.loads(called_kwargs.get('data')), body)

        self.requests['POST'].assert_not_called()
        self.requests['DELETE'].assert_not_called()


class TestDeRegister(unittest.TestCase):
    def setUp(self):
        self.host = "127.0.1.1"
        self.port = 9103
        self.req_types = ["DELETE", "GET", "POST", "PUT"]
        self.config = {"promreg_url": "http://127.0.0.1:12321", "promreg_authtoken": "abc"}
        os.environ['JUJU_UNIT_NAME'] = 'test_juju_unit'
        self.url = self.config['promreg_url'] + '/targets/' + '{}:{}'.format(self.host, self.port)
        self.headers = {'AuthToken': self.config['promreg_authtoken']}

        patched_hookenv_charm_name = mock.patch('charmhelpers.core.hookenv.charm_name', return_value='test_charm')
        patched_hookenv_charm_name.start()

        patched_hookenv_config = mock.patch('charmhelpers.core.hookenv.config', return_value=self.config)
        patched_hookenv_config.start()

        execution_environment = {'env': {'JUJU_MODEL_NAME': 'test_juju_model'}}
        patched_hookenv_execution_enviroment = mock.patch('charmhelpers.core.hookenv.execution_environment',
                                                          return_value=execution_environment)
        patched_hookenv_execution_enviroment.start()

        patched_hookenv_log = mock.patch('charmhelpers.core.hookenv.log')
        self.hookenv_log = patched_hookenv_log.start()

        self.requests = {}
        for rtype in self.req_types:
            patched_requests = mock.patch('requests.' + rtype.lower())
            self.requests[rtype] = patched_requests.start()

        self.exists = mock.MagicMock()
        self.exists.status_code = 200
        self.exists.labels = {"labelname1": "labelvalue1"}
        json_mock = mock.MagicMock(return_value=[{"Host": "127.0.0.1", "labels": self.exists.labels}])
        self.exists.json = json_mock
        self.exists.text = json.dumps([{"Host": "127.0.0.1", "labels": self.exists.labels}])

    def testDelete(self):
        self.requests['GET'].return_value = self.exists  # Needed to set status code
        self.requests['DELETE'].return_value = self.exists  # Needed to set status code
        charms.promreg.deregister(self.host, self.port)

        body = {'comment': 'Delete by charm test_charm'}
        called_kwargs = self.requests['DELETE'].call_args[1]
        self.assertEqual(called_kwargs.get('url'), self.url)
        self.assertEqual(called_kwargs.get('headers'), self.headers)
        self.assertEqual(json.loads(called_kwargs.get('data')), body)

        self.requests['POST'].assert_not_called()
        self.requests['PUT'].assert_not_called()

    def testAlreadyGone(self):
        self.exists.text = 'null'
        self.requests['GET'].return_value = self.exists  # Needed to set status code

        self.requests['POST'].assert_not_called()
        self.requests['PUT'].assert_not_called()
        self.requests['DELETE'].assert_not_called()
