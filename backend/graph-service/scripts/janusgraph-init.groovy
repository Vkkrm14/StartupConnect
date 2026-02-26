// JanusGraph Server Initialization Script
// This script is executed when the Gremlin Server starts
// Purpose: Initialize any global variables and configurations needed for remote connections

// Note: With JanusGraphManager, the graph instance is managed by the server
// and the traversal source 'g' is automatically made available to remote clients
// through the graphs configuration in gremlin-server.yaml

// Log successful initialization
println "JanusGraph initialization script loaded successfully"
println "Server ready to accept remote connections"
