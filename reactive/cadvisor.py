import subprocess
import requests
import os
import tempfile

from charmhelpers import fetch
from charmhelpers.core import hookenv, host, unitdata
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, when_any, set_flag, clear_flag, hook
from charms.reactive.helpers import data_changed
from charms import promreg

SVCNAME = 'cadvisor'
PKGNAMES = 'cadvisor'
CADVISOR = '/etc/default/cadvisor'
CADVISOR_TMPL = 'cadvisor.j2'


# Variables
db = unitdata.kv()
hook_data = unitdata.HookData()


# Utilities
def check_ports(new_port):
    if db.get('cadvisor.port') != new_port:
        hookenv.open_port(new_port)
        if db.get('cadvisor.port'):  # Dont try to close non existing ports
            hookenv.close_port(db.get('cadvisor.port'))
        db.set('cadvisor.port', new_port)


# States
@when_not('cadvisor.installed')
def install_cadvisor():
    config = hookenv.config()
    install_opts = ('install_sources', 'install_keys')
    hookenv.status_set('maintenance', 'Installing cAdvisor')
    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'

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
        set_flag('cadvisor.installed')
    else:
        if install_opts:
            for opt in install_opts:
                fetch.configure_sources(update=True)
        fetch.apt_update()
        fetch.apt_install(PKGNAMES)
        hookenv.status_set('active', 'Completed installing cAdvisor')
        set_flag('cadvisor.installed')


@when('cadvisor.installed')
@when_any('config.changed.port', 'config.changed.standalone')
def setup_cadvisor():
    config = hookenv.config()
    settings = {'config': config}
    render(source=CADVISOR_TMPL,
           target=CADVISOR,
           context=settings,
           perms=0o640,
           )
    check_ports(config.get('port'))
    set_flag('cadvisor.do-restart')


@when('cadvisor.do-restart')
def restart_cadvisor():
    msg = 'Restarting {}'.format(SVCNAME)
    hookenv.log(msg)
    hookenv.status_set('maintenance', msg)
    host.service_restart(SVCNAME)
    hookenv.status_set('active', 'Ready')
    clear_flag('cadvisor.do-restart')


@when_not('prometheus-client.available')
def setup_prometheus_client_relation():
    hookenv.status_set('waiting', 'Waiting for: prometheus')


@when('prometheus-client.available')
def prometheus_client_available(prometheus_client):
    config = hookenv.config() 
    prometheus_client.configure(port=config.get('port'))

    for relation_id in hookenv.relation_ids():
        hookenv.relation_set(relation_id, {'principal-unit': db.get('cadvisor.principal_unit')})
    hookenv.status_set('active', 'Ready')


@when('juju-info.available')
def juju_info_available():
    db.set('cadvisor.principal_unit', os.environ.get('JUJU_PRINCIPAL_UNIT'))

 
@hook('stop')
def hook_handler_stop():
    set_flag('cadvisor.stopped')


@when('cadvisor.stopped')
@when_not('juju-info.available')
def remove_packages():
   fetch.apt_purge(PKGNAMES, fatal=True)
