import subprocess
import requests
import os

from charmhelpers import fetch
from charmhelpers.core import hookenv, host, unitdata
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, set_state, remove_state, hook
from charms.reactive.helpers import any_file_changed, is_state, data_changed

SVCNAME = 'cadvisor'
CADVISOR = '/etc/default/cadvisor'
CADVISOR_TMPL = 'cadvisor.j2'
proxy=""

@when_not('cadvisor.installed')
def install_cadvisor():
    config = hookenv.config()
    install_opts = ('install_sources', 'install_keys')
    hookenv.status_set('maintenance', 'Installing cAdvisor')

    if config.changed('install_file') and config.get('install_file', False):
        hookenv.status_set('maintenance', 'Installing deb pkgs')
        pkg_file = '/tmp/cadvisor.deb'
        with open(pkg_file, 'wb') as f:
            r = requests.get(config.get('install_file'), stream=True,
                             proxies=proxy)
            for block in r.iter_content(1024):
                f.write(block)
        subprocess.check_call(['dpkg', '-i', pkg_file])
    elif any(config.changed(opt) for opt in install_opts):
        hookenv.status_set('maintenance', 'Installing deb pkgs')
        packages = ['cadvisor']
        fetch.configure_sources(update=True)
        fetch.apt_install(packages)
    set_state('cadvisor.installed')
    hookenv.status_set('active', 'Completed installing cAdvisor')
# Install from --resources cadvisor=cadvisor.deb
#    deb_path = hookenv.resource_get('cadvisor')
#    if deb_path and hookenv.os.stat(deb_path).st_size != 0 and deb_path.endswith(".deb"):
#        subprocess.check_call(['dpkg', '-i', deb_path])
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
           owner='root', group='root',
           perms=0o640,
           )
    check_ports(config.get('port'))
    set_state('cadvisor.configured')
    remove_state('cadvisor.started')
    hookenv.status_set('active', 'Completed configuring grafana')

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
    hookenv.status_set('active', 'Ready')
