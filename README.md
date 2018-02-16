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

## TODO

Currently the charm is set up to run cadvisor as 'standalone' as there's no docker used for trusty systems.
More configuration options will be added as needed.
