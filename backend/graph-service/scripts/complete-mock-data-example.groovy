// Complete example showing how to properly initialize JanusGraph and add data
// This works both in remote console and when executing scripts directly

println "=== JanusGraph Initialization & Mock Data Example ==="

// ============================================================
// STEP 1: Initialize Graph and Traversal
// ============================================================

// When running via Gremlin Server, 'graph' is automatically available
// from the server configuration (janusgraph-server.yaml)
// We just create the traversal source from the existing graph
g = graph.traversal()

println "\nGraph instance: " + graph
println "Traversal source: " + g
println "Graph is open: " + graph.isOpen()

// ============================================================
// STEP 2: Check Initial State
// ============================================================

println "\nInitial vertex count: " + g.V().count().next()

// ============================================================
// STEP 3: Add Mock Data - Users
// ============================================================

println "\n--- Adding Users ---"

// User 1: Alice (Entrepreneur)
alice = g.addV("user")
    .property("user_id", "user_001")
    .property("name", "Alice Johnson")
    .property("email", "alice@example.com")
    .property("user_type", "entrepreneur")
    .property("created_at", new Date().getTime())
    .next()
println "Added: Alice Johnson (Entrepreneur)"

// User 2: Bob (Investor)
bob = g.addV("user")
    .property("user_id", "user_002")
    .property("name", "Bob Smith")
    .property("email", "bob@example.com")
    .property("user_type", "investor")
    .property("created_at", new Date().getTime())
    .next()
println "Added: Bob Smith (Investor)"

// User 3: Charlie (Mentor)
charlie = g.addV("user")
    .property("user_id", "user_003")
    .property("name", "Charlie Davis")
    .property("email", "charlie@example.com")
    .property("user_type", "mentor")
    .property("created_at", new Date().getTime())
    .next()
println "Added: Charlie Davis (Mentor)"

// ============================================================
// STEP 4: Add Mock Data - Startups
// ============================================================

println "\n--- Adding Startups ---"

// Startup 1: TechCorp
techcorp = g.addV("startup")
    .property("startup_id", "startup_001")
    .property("name", "TechCorp AI")
    .property("industry", "Artificial Intelligence")
    .property("stage", "seed")
    .property("founded_year", 2024)
    .next()
println "Added: TechCorp AI"

// Startup 2: FinanceFlow
financeflow = g.addV("startup")
    .property("startup_id", "startup_002")
    .property("name", "FinanceFlow")
    .property("industry", "FinTech")
    .property("stage", "series_a")
    .property("founded_year", 2023)
    .next()
println "Added: FinanceFlow"

// ============================================================
// STEP 5: Add Relationships (Edges)
// ============================================================

println "\n--- Adding Relationships ---"

// Alice founded TechCorp
g.V(alice).addE("founded")
    .to(g.V(techcorp))
    .property("role", "CEO")
    .property("since", 2024)
    .next()
println "Alice founded TechCorp AI"

// Bob invested in TechCorp
g.V(bob).addE("invested_in")
    .to(g.V(techcorp))
    .property("amount", 500000)
    .property("date", "2024-06-15")
    .next()
println "Bob invested in TechCorp AI"

// Charlie mentors Alice
g.V(charlie).addE("mentors")
    .to(g.V(alice))
    .property("since", 2023)
    .property("focus_area", "product_development")
    .next()
println "Charlie mentors Alice"

// Alice knows Bob (trust relationship)
g.V(alice).addE("trusts")
    .to(g.V(bob))
    .property("trust_score", 0.85)
    .property("established", "2024-01-10")
    .next()
println "Alice trusts Bob"

// ============================================================
// STEP 6: Commit Transaction
// ============================================================

println "\n--- Committing Transaction ---"
graph.tx().commit()
println "Transaction committed successfully"

// ============================================================
// STEP 7: Query the Data
// ============================================================

println "\n=== Data Summary ==="
println "Total vertices: " + g.V().count().next()
println "Total edges: " + g.E().count().next()

println "\nUsers in the graph:"
g.V().hasLabel("user").values("name").each { println "  - " + it }

println "\nStartups in the graph:"
g.V().hasLabel("startup").values("name").each { println "  - " + it }

println "\nAlice's connections:"
g.V().has("user", "name", "Alice Johnson").out().values("name").each { println "  - " + it }

println "\nInvestors in TechCorp:"
g.V().has("startup", "name", "TechCorp AI").in("invested_in").values("name").each { println "  - " + it }

println "\n=== Mock Data Setup Complete ==="
