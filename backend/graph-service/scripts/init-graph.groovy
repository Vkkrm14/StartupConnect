// Access graph through JanusGraphManager
// The manager is available in the script context when using JanusGraphManager

def globals = [:]

try {
    // Get the graph instance from the manager's graph map
    // The graph name 'graph' must match the name in gremlin-server.yaml
    def graphInstance = graphs['graph']
    
    if (graphInstance != null) {
        // Create traversal source and add to globals
        globals['g'] = graphInstance.traversal()
        println "✅ Traversal source 'g' successfully bound to graph instance"
    } else {
        println "⚠️ WARNING: Graph instance 'graph' not found in graphs map"
        println "Available graphs: ${graphs.keySet()}"
    }
} catch (Exception e) {
    println "❌ ERROR binding traversal source: ${e.message}"
    e.printStackTrace()
}