// Initialize graph traversal source for remote connections
def globals = [:]

// Get the graph instance from the server context
if (graph != null) {
    globals["g"] = graph.traversal()
    println "Graph traversal source 'g' initialized successfully"
} else {
    println "WARNING: graph variable is null, cannot initialize traversal source"
}
