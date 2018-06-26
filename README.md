# cAdvisor

This project builds a reactive layered charm for [Advisor](https://github.com/google/cadvisor).

## Build

In this directory, with `$JUJU_REPOSITORY` set:

    $ charm build

## Usage

This charm is a subordinate that adds an HTTP metric scrape endpoint to prometheus.

    $ juju deploy cadvisor
    $ juju deploy prometheus
    $ juju add-relation machine cadvisor
    $ juju add-relation cadvisor prometheus:target

This will expose HTTP operational metrics on all machine units running containers, which
prometheus will pull from.   

Basic functionality to support LXC metrics for prometheus on Trusty systems.

## TODO

More configuration options will be added as needed.
* Add options via DAEMON_ARGS variable in /etc/init.d/cadvisor
