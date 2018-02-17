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
import json
import requests
import socket

from charmhelpers.core import hookenv


class PromRegClientError(Exception):
    pass


def build_target(host, port):
    """
    :param host: The host or ip of the target. If None the ip of the interface with the default gw is used.
    :param port: The port of the target.
    :return: A string representing the prometheus target address.
    """
    if host is None:
        host = hookenv.unit_private_ip()
    return '{}:{}'.format(host, port)


def deregister(host, port):
    """ De-register a target with the Prometheus Registartion service
    :param host: The host or ip of the target. If None the ip of the interface with the default gw is used.
    :param port: The port of the target.
    """
    target = build_target(host, port)
    charm_name = hookenv.charm_name()

    exists = promreg_req('GET', target, None)
    if exists is None:
        return
    if exists.status_code != requests.codes.ok:
        raise PromRegClientError('error {} deleting target {}, {}'.format(exists.status_code, target, exists.text))

    if exists.text == 'null':  # target doesn't exist
        return

    r = promreg_req('DELETE', target, {'comment': 'Delete by charm {}'.format(charm_name)})
    if r.status_code != requests.codes.ok:
        # if the target is already de-registered that is success
        if r.status_code == 500 and r.text == "Storage Error host not found unable to delete":
            return
        raise PromRegClientError('500 error deregistering target {}, {}'.format(target, r.text))


def get_default_labels():
    """
    :return: A dictionary containing the default labels.
    """
    labels = {
        'host': socket.gethostname(),
        'juju_unit': hookenv.local_unit()
    }

    # JUJU_MODEL_NAME is used by Juju2, Juju_ENV_NAME by Juju1
    if 'JUJU_MODEL_NAME' in hookenv.execution_environment()['env']:
        labels['juju_model'] = hookenv.execution_environment()['env']['JUJU_MODEL_NAME']
    else:
        labels['juju_env'] = hookenv.execution_environment()['env']['JUJU_ENV_NAME']

    return labels


def promreg_req(rtype, target, body):
    """ A wrapper around requests that builds the appropriate url and sets the authtoken.
    :param rtype: DELETE, GET, POST or PUT
    :param target: The host(or ip):port of the target.
    :param body: A dictionary containing body content
    :return: The return of the approrpiate requests call or None if no promreg_url is defined.
    """
    config = hookenv.config()
    if config['promreg_url'] == '':
        hookenv.log('promreg_url is unset unable to register or de-register targets')
        return None
    url = config['promreg_url'] + '/targets/' + target
    headers = {'AuthToken': config['promreg_authtoken'].rstrip('\n')}

    if rtype == 'DELETE':
        return requests.delete(url=url, headers=headers, data=json.dumps(body))
    elif rtype == 'GET':
        return requests.get(url=url, headers=headers)
    elif rtype == 'POST':
        return requests.post(url=url, headers=headers, data=json.dumps(body))
    elif rtype == 'PUT':
        return requests.put(url=url, headers=headers, data=json.dumps(body))
    else:
        raise PromRegClientError('type {} is invalid for promreg_req'.format(type))


def register(host, port, custom_labels=None):
    """ Register a target with the Prometheus Registartion service or update labels if needed.
    :param host: The host or ip of the target. If None the ip of the interface with the default gw is used.
    :param port: The port of the target.
    :param custom_labels: An optional dictionary of labels and values to add when registering the service
    """
    target = build_target(host, port)
    labels = get_default_labels()
    if custom_labels is not None:  # Any specified labels should override default values
        labels.update(custom_labels)

    exists = promreg_req('GET', target, None)
    if exists is None:
        return
    if exists.status_code != requests.codes.ok:
        raise PromRegClientError('error {} registering target {}, {}'.format(exists.status_code, target, exists.text))

    comment = 'Added by charm {}'.format(hookenv.charm_name())
    if exists.text != 'null':  # target exists possibly update
        if labels == exists.json()[0]['labels']:
            return

        r = promreg_req('PUT', target, {'comment': comment, 'labels': labels})
    else:
        r = promreg_req('POST', target, {'comment': comment, 'labels': labels})

    if r.status_code < 200 or r.status_code >= 300:
        raise PromRegClientError('error {} registering target {}, {}'.format(r.status_code, target, r.text))
