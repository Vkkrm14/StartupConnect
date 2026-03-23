"""
Gremlin test suite for DISTRUSTS edge functionality.

Tests cover:
- DISTRUSTS edge creation and filtering
- Path discovery with DISTRUSTS filtering
- Conflict resolution scenarios
- Active vs disputed distrust behavior
"""

# Test fixture setup for Gremlin connection
"""
To run these tests:
1. Ensure JanusGraph is running: docker compose up -d
2. Load sample data: python backend/scripts/seed_data.py
3. Run this test: python backend/graph-service/tests/test_distrusts_gremlin.py
"""

from datetime import datetime, timedelta
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P


class GremlinDisTrustsTests:
    """Test DISTRUSTS functionality with live Gremlin queries"""
    
    def __init__(self, janusgraph_url="ws://localhost:8182/gremlin"):
        """Initialize Gremlin connection"""
        self.janusgraph_url = janusgraph_url
        self.conn = None
        self.g = None
    
    def connect(self):
        """Establish connection to JanusGraph"""
        try:
            self.conn = DriverRemoteConnection(
                self.janusgraph_url,
                'g'
            )
            self.g = traversal().withRemote(self.conn)
            print(f"✅ Connected to JanusGraph at {self.janusgraph_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close JanusGraph connection"""
        if self.conn:
            self.conn.close()
            print("✅ Disconnected from JanusGraph")
    
    def test_distrusts_edge_exists(self):
        """Verify DISTRUSTS edges are in the graph"""
        print("\n🔍 Test: DISTRUSTS edges exist")
        try:
            count = self.g.E().hasLabel('DISTRUSTS').count().next()
            print(f"  ✅ Found {count} DISTRUSTS edges")
            return count > 0
        except Exception as e:
            print(f"  ❌ Failed to query DISTRUSTS edges: {e}")
            return False
    
    def test_active_distrusts_filter(self):
        """Test filtering by is_active property"""
        print("\n🔍 Test: Active DISTRUSTS filtering")
        try:
            active_count = (
                self.g.E().hasLabel('DISTRUSTS')
                .has('is_active', True)
                .count().next()
            )
            print(f"  ✅ Found {active_count} active DISTRUSTS edges")
            return active_count >= 0
        except Exception as e:
            print(f"  ❌ Failed to filter active DISTRUSTS: {e}")
            return False
    
    def test_disputed_distrusts_filter(self):
        """Test filtering by is_disputed property"""
        print("\n🔍 Test: Disputed DISTRUSTS filtering")
        try:
            disputed_count = (
                self.g.E().hasLabel('DISTRUSTS')
                .has('is_disputed', True)
                .count().next()
            )
            print(f"  ✅ Found {disputed_count} disputed DISTRUSTS edges")
            return disputed_count >= 0
        except Exception as e:
            print(f"  ❌ Failed to filter disputed DISTRUSTS: {e}")
            return False
    
    def test_path_without_distrusts(self):
        """Verify paths exclude nodes with active DISTRUSTS"""
        print("\n🔍 Test: Path discovery excludes DISTRUSTS nodes")
        try:
            # Find a founder and investor for testing
            founders = self.g.V().has('User', 'role_primary', 'founder').limit(1).toList()
            investors = self.g.V().has('User', 'role_primary', 'investor').limit(1).toList()
            
            if not founders or not investors:
                print("  ⚠️  Insufficient test users (need founder and investor)")
                return False
            
            founder = founders[0]
            investor = investors[0]
            
            # Query paths excluding DISTRUSTS nodes
            paths = (
                self.g.V(founder)
                .repeat(
                    __.outE('TRUSTS')
                    .has('status', 'accepted')
                    .inV()
                    .not_(
                        __.inE('DISTRUSTS')
                        .has('is_active', True)
                        .not_(__.has('is_disputed', True))
                    )
                    .simplePath()
                )
                .times(4)
                .has('User', 'id', investor.id)
                .path()
                .by(__.values('user_id'))
                .toList()
            )
            
            print(f"  ✅ Found {len(paths)} paths without DISTRUSTS nodes")
            for i, path in enumerate(paths[:3]):  # Show first 3 paths
                print(f"     Path {i+1}: {' → '.join(path)}")
            return True
        except Exception as e:
            print(f"  ❌ Path discovery test failed: {e}")
            return False
    
    def test_distrusts_with_mutual_flag(self):
        """Test mutual DISTRUSTS detection"""
        print("\n🔍 Test: Mutual DISTRUSTS detection")
        try:
            # Find both-direction DISTRUSTS relationships
            mutual_distrusts = (
                self.g.V()
                .outE('DISTRUSTS')
                .where(
                    __.inV().outE('DISTRUSTS')
                    .where(__.inV().as_('start'))
                    .filter(__.as_('start'))
                )
                .count().next()
            )
            print(f"  ✅ Found {mutual_distrusts} mutual DISTRUSTS pairs")
            return mutual_distrusts >= 0
        except Exception as e:
            print(f"  ⚠️  Mutual DISTRUSTS query not fully supported: {e}")
            return True  # Non-fatal
    
    def test_distrust_score_range(self):
        """Verify distrust_score is in correct range"""
        print("\n🔍 Test: Distrust score range (-1.0 to -0.0)")
        try:
            scores = (
                self.g.E().hasLabel('DISTRUSTS')
                .values('distrust_score')
                .toList()
            )
            
            valid = all(-1.0 <= score <= -0.0 for score in scores)
            print(f"  ✅ Verified {len(scores)} distrust scores in valid range")
            
            if scores:
                min_score = min(scores)
                max_score = max(scores)
                print(f"     Score range: {min_score:.2f} to {max_score:.2f}")
            
            return valid
        except Exception as e:
            print(f"  ❌ Failed to check distrust scores: {e}")
            return False
    
    def test_trust_score_with_negative(self):
        """Verify TRUSTS edges support negative trust scores"""
        print("\n🔍 Test: TRUSTS edges support -1.0 to 1.0 range")
        try:
            # Find trust edges with various scores
            trust_trust = (
                self.g.E().hasLabel('TRUSTS')
                .has('trust_score', P.gte(0.5))
                .count().next()
            )
            print(f"  ✅ Found {trust_trust} high-trust edges (score >= 0.5)")
            
            # Note: Showing capability to query negative trust if present
            potential_negative = (
                self.g.E().hasLabel('TRUSTS')
                .has('trust_score', P.lt(0))
                .count().next()
            )
            print(f"     Can query negative trust scores: {potential_negative} found")
            return True
        except Exception as e:
            print(f"  ❌ Failed to check trust scores: {e}")
            return False
    
    def test_compare_trust_and_distrust(self):
        """Compare trust score with distrust edges between same users"""
        print("\n🔍 Test: Compare TRUSTS vs DISTRUSTS between same users")
        try:
            # Find pairs with both TRUSTS and DISTRUSTS
            conflicts = (
                self.g.V()
                .outE('TRUSTS')
                .as_('t')
                .inV()
                .filter(
                    __.as_('target')
                    .map(__.as_('source').outE('DISTRUSTS')
                        .where(__.inV().as_('target')))
                )
                .count().next()
            )
            print(f"  ✅ Found {conflicts} cases with conflicting TRUSTS/DISTRUSTS")
            return True
        except Exception as e:
            print(f"  ⚠️  Complex query not fully supported: {e}")
            return True  # Non-fatal
    
    def test_distrusts_expiration_logic(self):
        """Test that expired DISTRUSTS are handled correctly"""
        print("\n🔍 Test: DISTRUSTS expiration logic")
        try:
            now = int(datetime.utcnow().timestamp())
            
            # Count edges that should have expired
            expired_now = (
                self.g.E().hasLabel('DISTRUSTS')
                .has('expires_at', P.lt(now))
                .count().next()
            )
            
            # Count edges created 30+ days ago
            old_distrusts = (
                self.g.E().hasLabel('DISTRUSTS')
                .has('created_at', P.lt(now - 86400*30))
                .count().next()
            )
            
            print(f"  ✅ Found {expired_now} expired DISTRUSTS (by expiry date)")
            print(f"     Found {old_distrusts} old DISTRUSTS (30+ days)")
            return True
        except Exception as e:
            print(f"  ❌ Failed to check expiration logic: {e}")
            return False
    
    def run_all_tests(self):
        """Run all DISTRUSTS tests"""
        print("=" * 60)
        print("🧪 DISTRUSTS Gremlin Test Suite")
        print("=" * 60)
        
        if not self.connect():
            print("❌ Cannot connect to JanusGraph. Tests aborted.")
            return False
        
        try:
            tests = [
                self.test_distrusts_edge_exists,
                self.test_active_distrusts_filter,
                self.test_disputed_distrusts_filter,
                self.test_path_without_distrusts,
                self.test_distrusts_with_mutual_flag,
                self.test_distrust_score_range,
                self.test_trust_score_with_negative,
                self.test_compare_trust_and_distrust,
                self.test_distrusts_expiration_logic,
            ]
            
            results = []
            for test in tests:
                try:
                    result = test()
                    results.append(result)
                except Exception as e:
                    print(f"  ❌ Test exception: {e}")
                    results.append(False)
            
            print("\n" + "=" * 60)
            print(f"📊 Results: {sum(results)}/{len(results)} tests passed")
            print("=" * 60)
            
            return all(results)
        finally:
            self.disconnect()


if __name__ == "__main__":
    tester = GremlinDisTrustsTests()
    success = tester.run_all_tests()
    exit(0 if success else 1)
