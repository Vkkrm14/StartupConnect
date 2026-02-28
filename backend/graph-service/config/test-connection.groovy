// Test connection script for Gremlin Console
// To enable session (variables persist), add "session" at the end:
// :remote connect tinkerpop.server conf/remote.yaml session
:remote connect tinkerpop.server conf/remote.yaml
:remote console

// When using :remote console, 'graph' is already provided by the server
// Just create the traversal source from the existing graph
g = graph.traversal()

// Test the connection
g.V().count()
