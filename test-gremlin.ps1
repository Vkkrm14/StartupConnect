# Test JanusGraph Gremlin Console Connection
Write-Host "`n=== Testing JanusGraph Remote Connection ===" -ForegroundColor Cyan
Write-Host "Creating test script..." -ForegroundColor Yellow

# Create test commands file
@"
:remote connect tinkerpop.server conf/remote.yaml
:remote console
g.V().count()
:exit
"@ | Out-File -FilePath ".\test-commands.txt" -Encoding ascii

# Copy to container
docker cp ".\test-commands.txt" trustgraph-janusgraph:/tmp/test-commands.txt

# Run the test
Write-Host "`nExecuting commands in Gremlin Console..." -ForegroundColor Yellow
docker exec trustgraph-janusgraph bash -c "./bin/gremlin.sh < /tmp/test-commands.txt"

# Cleanup
Remove-Item ".\test-commands.txt" -ErrorAction SilentlyContinue

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
Write-Host "Look for '==>0' in the output above to confirm it works!" -ForegroundColor Green
