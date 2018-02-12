# Juju-Info Interface

The juju info interface is a special and implicit relationship that works with
subordinate charms. When building from layers, if your subordinate uses this
interface, you will implicitly receive private-address.

There is no provides or peering mechanism on this interface.


### States

`{{relation-name}}.available`

`{{relation-name}}.connected`

Both states signify the subordinate is successfully connected to the parent
"container".

Note: these states key off of what the charm author names the relationship
which should *not* be the name of the interface:

An example of a properly implemented relationship would resemble the following:


```yaml
requires:
  host-system:
    interface: juju-info
```

The respective states in your charm would then be:

```python
@when_any('host-system.available', 'host-system.connected')
```

