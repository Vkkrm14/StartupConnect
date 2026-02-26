// Test connection script for Gremlin Console
:remote connect tinkerpop.server conf/remote.yaml
:remote console
g.V().count()
