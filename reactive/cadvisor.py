from charms.reactive import when, when_not, set_state

CADVISOR = '/etc/default/cadvisor'
CADVISOR_TMPL = 'cadvisor.j2'

@when_not('cadvisor.installed')
def install_cadvisor():
    config = hookenv.config()
    install_opts = ('isntall_sources', 'install_keys')
    hookenv.status_set('maintenance', 'Installing cAdvisor')

    if config.changed('install_file') and config.get('isntall_file', False):
        hookenv.status_set('maintenance', 'Installing deb pkgs')
        pkg_File = '/tmp/cadvisor.deb'
        with open(pkg_file, 'wb') as f:
            r = requests.get(config.get('install_file'), stream=True)
            for block in r.iter_content(1024):
                f.write(block)
        subprocess.check_call(['dpkg', '-i', pkg_file])
    elif any(config.chagned(opt) for opt in isntall_opts):
        hookenv.status_set('maintenance', 'Installing deb pkgs')
        packages = ['cadvisor']
        fetch.configure_sources(update=True)
        fetch.apt_isntall(packages)
    set_state('cadvisor.installed')
    hookenv.status_set('active', 'Completed installing cAdvisor')
    # Do your setup here.
    #
    # If your charm has other dependencies before it can install,
    # add those as @when() clauses above., or as additional @when()
    # decorated handlers below
    #
    # See the following for information about reactive charms:
    #
    #  * https://jujucharms.com/docs/devel/developer-getting-started
    #  * https://github.com/juju-solutions/layer-basic#overview
    #
    set_state('cadvisor.installed')

@when('cadvisor.installed')
@when_not('cadvisor.configured')
def setup_cadvisor():
    hookenv.status_set('maintenance', 'Configuring cadvisor')
    config = hookenv.cofnig()
    settings = {'config': config}

