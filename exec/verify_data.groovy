// Verify seed data in JanusGraph
:remote connect tinkerpop.server conf/remote.yaml
:remote console

println "===== VERTEX COUNTS ====="
println "Total vertices: " + g.V().count().next()
println "Users: " + g.V().hasLabel('User').count().next()
println "Startups: " + g.V().hasLabel('Startup').count().next()

println "\n===== EDGE COUNTS ====="
println "Total edges: " + g.E().count().next()
println "TRUSTS edges: " + g.E().hasLabel('TRUSTS').count().next()
println "FOUNDED edges: " + g.E().hasLabel('FOUNDED').count().next()
println "INVESTED_IN edges: " + g.E().hasLabel('INVESTED_IN').count().next()

println "\n===== SAMPLE USERS ====="
g.V().hasLabel('User').valueMap().limit(3).toList().each { println it }

println "\n===== SAMPLE STARTUPS ====="
g.V().hasLabel('Startup').valueMap().limit(2).toList().each { println it }

println "\n===== SAMPLE TRUST EDGES ====="
g.E().hasLabel('TRUSTS').limit(2).valueMap().toList().each { println it }

:remote console
:exit
