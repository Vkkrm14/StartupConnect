@echo off
echo Testing JanusGraph Remote Connection...
echo.

docker exec trustgraph-janusgraph bash -c "
cat > /tmp/test-remote.groovy << 'EOF'
:remote connect tinkerpop.server conf/remote.yaml
:> 
:remote console
:> 
g.V().count()
:> 
:exit
EOF

./bin/gremlin.sh < /tmp/test-remote.groovy 2>&1 | grep -E 'Configured|All scripts|==>'
"

echo.
echo If you see '==^>0' above, the connection works!
