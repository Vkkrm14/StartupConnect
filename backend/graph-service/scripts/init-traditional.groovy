// Traditional Gremlin Server initialization script
// Works when NOT using JanusGraphManager

def globals = [:]

// The 'graph' variable is automatically available
// because it's defined in graphs: section
if (graph != null) {
    globals['g'] = graph.traversal()
    println "✅ Traversal source 'g' successfully bound (Traditional mode)"
} else {
    println "❌ ERROR: graph variable is null"
}
