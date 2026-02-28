// Test script to add mock data to JanusGraph
// This demonstrates the correct ways to add data

println "=== Testing JanusGraph Mock Data ==="
:remote connect tinkerpop.server conf/remote.yaml session:remote connect tinkerpop.server conf/remote.yaml session:remote connect tinkerpop.server conf/remote.yaml session
// When running this script via Gremlin Server (remote or direct execution),
// the 'graph' object is already available from server configuration in janusgraph-server.yaml
// We just need to create the traversal source
g = graph.traversal()

println "Graph: " + graph
println "Traversal: " + g

// METHOD 1: Direct values (works in sessionless mode)
println "\n1. Adding vertex with direct values..."
v1 = graph.addVertex(label, "person", "name", "Alice", "age", 30)
println "Added vertex: " + v1

// METHOD 2: Multiple statements on one line with semicolon (sessionless mode)
println "\n2. Adding vertex with variable on same line..."
name = "Bob"; age = 25; v2 = graph.addVertex(label, "person", "name", name, "age", age)
println "Added vertex: " + v2

// METHOD 3: Using graph traversal (recommended approach)
println "\n3. Adding vertices using traversal..."
g.addV("person").property("name", "Charlie").property("age", 35).next()
g.addV("person").property("name", "Diana").property("age", 28).next()

// Add some relationships
println "\n4. Adding edges..."
alice = g.V().has("person", "name", "Alice").next()
bob = g.V().has("person", "name", "Bob").next()
alice.addEdge("knows", bob, "since", 2020)

// Query the data
println "\n5. Querying data..."
println "Total vertices: " + g.V().count().next()
println "All people: "
g.V().hasLabel("person").values("name").each { println "  - " + it }

println "\n=== Test Complete ==="
graph.tx().commit()
