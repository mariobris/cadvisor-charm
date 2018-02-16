import subprocess
import requests
import os
import tempfile

from charmhelpers import fetch
from charmhelpers.core import hookenv, host, unitdata
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, set_state, remove_state, hook
from charms.reactive.helpers import any_file_changed, is_state, data_changed

SVCNAME = 'cadvisor'
PKGNAMES = 'cadvisor'
CADVISOR = '/etc/default/cadvisor'
CADVISOR_TMPL = 'cadvisor.j2'

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
        hookenv.status_set('maintenance', 'Installing deb pkgs')
        with tempfile.NamedTemporaryFile(suffix='.deb') as f:
            r = requests.get(config.get('install_file'), stream=True,
                             proxies=proxy)
            for block in r.iter_content(1024):
                f.write(block)
            f.flush()
            subprocess.check_call(['dpkg', '-i', f.name])
    elif any(config.changed(opt) for opt in install_opts):
        hookenv.status_set('maintenance', 'Installing deb pkgs')
        packages = ['cadvisor']
        fetch.configure_sources(update=True)
        fetch.apt_install(packages)
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

def check_ports(new_port):
    kv = unitdata.kv()
    if kv.get('cadvisor.port') != new_port:
        hookenv.open_port(new_port)
        if kv.get('cadvisor.port'):  # Dont try to close non existing ports
            hookenv.close_port(kv.get('cadvisor.port'))
        kv.set('cadvisor.port', new_port)

@when('cadvisor.started')
@when_not('target.available')
def setup_target_relation():
    hookenv.status_set('waiting', 'Waiting for: prometheus')

@when('target.available')
def configure_cadvisor_relation(target):
    config = hookenv.config() 
    if data_changed('target.config', config):
      try: 
        hostname=hookenv.network_get_primary_address('target')
      except NotImplementedError:
        hostname=hookenv.unit_get('private-address')
      target.configure(hostname=hostname, port=config.get('port'))
      hookenv.status_set('active', 'Ready')

    principal_unit = get_principal_unit()
    for conv in target.conversations():
        conv.set_remote('principal-unit', principal_unit)

@when('host.available')
def host_system_available():
    kv = unitdata.kv()
    for conv in host.conversations():
       kv.set('cadvisor.principal_unit', conv.get_remote('private-address')) 

def get_principal_unit():
    '''Return the principal unit for this subordinate.'''
    kv = unitdata.kv()
    return kv.get('cadvisor.principal_unit')

@when('config.changed')
def cadvisor_reconfigure():
    remove_state('cadvisor.configured')

@hook('stop')
def hook_handler_stop():
    set_state('cadvisor.stopped')

@when('cadvisor.stopped')
@when_not('host.available')
def remove_packages():
   fetch.apt_purge(PKGNAMES, fatal=True)
