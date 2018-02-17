import subprocess
import requests
import os
import tempfile

from charmhelpers import fetch
from charmhelpers.core import hookenv, host, unitdata
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, set_state, remove_state, hook
from charms.reactive.helpers import any_file_changed, is_state, data_changed
from charms import promreg

SVCNAME = 'cadvisor'
PKGNAMES = 'cadvisor'
CADVISOR = '/etc/default/cadvisor'
CADVISOR_TMPL = 'cadvisor.j2'

# Utilities
def check_ports(new_port):
    kv = unitdata.kv()
    if kv.get('cadvisor.port') != new_port:
        hookenv.open_port(new_port)
        if kv.get('cadvisor.port'):  # Dont try to close non existing ports
            hookenv.close_port(kv.get('cadvisor.port'))
        kv.set('cadvisor.port', new_port)

# States
@when_not('cadvisor.installed')
def install_cadvisor():
    config = hookenv.config()
    install_opts = ('install_sources', 'install_keys')
    hookenv.status_set('maintenance', 'Installing cAdvisor')

    if config.get('http_proxy'):
        proxy = {"http": config.get('http_proxy'),
                 "https": config.get('http_proxy'),
                 }
    else:
        proxy = {}

    if config.get('install_file', False):
        with tempfile.NamedTemporaryFile(suffix='.deb') as f:
            r = requests.get(config.get('install_file'), stream=True,
                             proxies=proxy)
            for block in r.iter_content(1024):
                f.write(block)
            f.flush()
            subprocess.check_call(['dpkg', '-i', f.name])
        set_state('cadvisor.installed')
        hookenv.status_set('active', 'Completed installing cAdvisor')
        set_state('cadvisor.installed')
    elif any(config.changed(opt) for opt in install_opts):
        fetch.configure_sources(update=True)
        fetch.apt_update()
        fetch.apt_install(PKGNAMES)
        set_state('cadvisor.installed')
        hookenv.status_set('active', 'Completed installing cAdvisor')
        set_state('cadvisor.installed')

@when('cadvisor.installed')
@when_not('cadvisor.configured')
def setup_cadvisor():
    hookenv.status_set('maintenance', 'Configuring cadvisor')
    config = hookenv.config()
    settings = {'config': config}
    render(source=CADVISOR_TMPL,
           target=CADVISOR,
           context=settings,
           perms=0o640,
           )
    check_ports(config.get('port'))
    set_state('cadvisor.configured')
    remove_state('cadvisor.started')
    hookenv.status_set('active', 'Completed configuring cadvisor')

@when('cadvisor.configured')
@when_not('cadvisor.started')
def restart_cadvisor():
    if not host.service_running(SVCNAME):
        msg = 'Starting {}'.format(SVCNAME)
        hookenv.status_set('maintenance', msg)
        hookenv.log(msg)
        host.service_start(SVCNAME)
    elif any_file_changed([CADVISOR]):
        msg = 'Restarting {}'.format(SVCNAME)
        hookenv.log(msg)
        hookenv.status_set('maintenance', msg)
        host.service_restart(SVCNAME)
    set_state('cadvisor.started')
    hookenv.status_set('active', 'Ready')

@when('cadvisor.started')
@when_not('prometheus-client.available')
def setup_prometheus_client_relation():
    hookenv.status_set('waiting', 'Waiting for: prometheus')

@when('prometheus-client.available')
def configure_cadvisor_relation(prometheus_client):
    config = hookenv.config() 
    kv = unitdata.kv()
    if data_changed('prometheus-client.config', config):
      try: 
        hostname=hookenv.network_get_primary_address('prometheus-client')
      except NotImplementedError:
        hostname=hookenv.unit_get('private-address')
      prometheus_client.configure(hostname=hostname, port=config.get('port'))
      hookenv.status_set('active', 'Ready')

    principal_unit = kv.get('cadvisor.principal_unit')
    for conv in prometheus_client.conversations():
        conv.set_remote('principal-unit', principal_unit)

@when('juju-info.available')
def juju_info_available():
    kv = unitdata.kv()
    for relation_id in hookenv.relation_ids('juju-info'):
        for relation_data in hookenv.relations_for_id(relation_id):
            kv.set('cadvisor.principal_unit', relation_data['__unit__']) 

@when('config.changed')
def cadvisor_reconfigure():
    remove_state('cadvisor.configured')

@hook('stop')
def hook_handler_stop():
    set_state('cadvisor.stopped')

@when('cadvisor.stopped')
@when_not('juju-info.available')
def remove_packages():
   fetch.apt_purge(PKGNAMES, fatal=True)
