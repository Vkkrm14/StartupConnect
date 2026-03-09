"""
JanusGraph Schema Initialization Script

Creates vertex labels, edge labels, properties, and indices
for the TrustGraph ecosystem.
"""

import sys
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Since we can't directly execute Groovy from Python easily,
# this script provides the Gremlin/Groovy commands to run manually
# or via JanusGraph's gremlin console

SCHEMA_SCRIPT = """
// Connect to graph
graph = JanusGraphFactory.open('conf/janusgraph-cassandra elasticsearch')
mgmt = graph.openManagement()

// ========================================
// PROPERTY KEYS
// ========================================

// User properties
mgmt.makePropertyKey('user_id').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('name').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('role_primary').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('roles_secondary').dataType(String.class).cardinality(Cardinality.SET).make()
mgmt.makePropertyKey('domain_tags').dataType(String.class).cardinality(Cardinality.SET).make()
mgmt.makePropertyKey('geography').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('experience_years').dataType(Integer.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('reputation_score').dataType(Double.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('verification_status').dataType(String.class).cardinality(Cardinality.SINGLE).make()

// Startup properties
mgmt.makePropertyKey('startup_id').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('domain').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('stage').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('founded_year').dataType(Integer.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('funding_status').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('employee_count').dataType(Integer.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('visibility_level').dataType(String.class).cardinality(Cardinality.SINGLE).make()

// Organization properties
mgmt.makePropertyKey('org_id').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('type').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('domains').dataType(String.class).cardinality(Cardinality.SET).make()
mgmt.makePropertyKey('website').dataType(String.class).cardinality(Cardinality.SINGLE).make()

// Edge properties
mgmt.makePropertyKey('edge_id').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('trust_score').dataType(Double.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('strength_score').dataType(Double.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('recency_score').dataType(Double.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('interaction_count').dataType(Integer.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('successful_intros').dataType(Integer.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('endorsement_count').dataType(Integer.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('last_interaction_at').dataType(Long.class).cardinality(Cardinality.SINGLE).make()

// TRUSTS edge enhancement properties
mgmt.makePropertyKey('status').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('suspicion_flag').dataType(Boolean.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('domain_trust_scores').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('interaction_decay_factor').dataType(Double.class).cardinality(Cardinality.SINGLE).make()

// DISTRUSTS edge properties
mgmt.makePropertyKey('distrust_score').dataType(Double.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('reason_category').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('evidence_notes').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('is_active').dataType(Boolean.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('is_disputed').dataType(Boolean.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('moderator_reviewed').dataType(Boolean.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('expires_at').dataType(Long.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('mutual_distrust_reported').dataType(Boolean.class).cardinality(Cardinality.SINGLE).make()

// VOUCHES edge properties
mgmt.makePropertyKey('vouch_strength').dataType(Double.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('is_revoked').dataType(Boolean.class).cardinality(Cardinality.SINGLE).make()

// EigenTrust / reputation ranking
mgmt.makePropertyKey('eigen_trust_rank').dataType(Double.class).cardinality(Cardinality.SINGLE).make()

// Common properties
mgmt.makePropertyKey('created_at').dataType(Long.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('updated_at').dataType(Long.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('role').dataType(String.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('start_date').dataType(Long.class).cardinality(Cardinality.SINGLE).make()
mgmt.makePropertyKey('active').dataType(Boolean.class).cardinality(Cardinality.SINGLE).make()

// ========================================
// VERTEX LABELS
// ========================================

mgmt.makeVertexLabel('User').make()
mgmt.makeVertexLabel('Startup').make()
mgmt.makeVertexLabel('Organization').make()

// ========================================
// EDGE LABELS
// ========================================

mgmt.makeEdgeLabel('TRUSTS').multiplicity(MULTI).make()
mgmt.makeEdgeLabel('DISTRUSTS').multiplicity(MULTI).make()
mgmt.makeEdgeLabel('VOUCHES').multiplicity(MULTI).make()
mgmt.makeEdgeLabel('FOUNDED').multiplicity(MULTI).make()
mgmt.makeEdgeLabel('INVESTED_IN').multiplicity(MULTI).make()
mgmt.makeEdgeLabel('MEMBER_OF').multiplicity(MULTI).make()
mgmt.makeEdgeLabel('WORKED_WITH').multiplicity(MULTI).make()
mgmt.makeEdgeLabel('ENDORSED').multiplicity(MULTI).make()

// ========================================
// COMPOSITE INDICES (Exact Match)
// ========================================

// Unique indices for IDs
mgmt.buildIndex('userByUserId', Vertex.class).addKey(mgmt.getPropertyKey('user_id')).indexOnly(mgmt.getVertexLabel('User')).unique().buildCompositeIndex()
mgmt.buildIndex('startupByStartupId', Vertex.class).addKey(mgmt.getPropertyKey('startup_id')).indexOnly(mgmt.getVertexLabel('Startup')).unique().buildCompositeIndex()
mgmt.buildIndex('orgByOrgId', Vertex.class).addKey(mgmt.getPropertyKey('org_id')).indexOnly(mgmt.getVertexLabel('Organization')).unique().buildCompositeIndex()

// Query indices
mgmt.buildIndex('userByRole', Vertex.class).addKey(mgmt.getPropertyKey('role_primary')).indexOnly(mgmt.getVertexLabel('User')).buildCompositeIndex()
mgmt.buildIndex('userByGeography', Vertex.class).addKey(mgmt.getPropertyKey('geography')).indexOnly(mgmt.getVertexLabel('User')).buildCompositeIndex()
mgmt.buildIndex('startupByStage', Vertex.class).addKey(mgmt.getPropertyKey('stage')).indexOnly(mgmt.getVertexLabel('Startup')).buildCompositeIndex()

// TRUSTS edge status index (pending/accepted/rejected lookups)
mgmt.buildIndex('trustsByStatus', Edge.class).addKey(mgmt.getPropertyKey('status')).indexOnly(mgmt.getEdgeLabel('TRUSTS')).buildCompositeIndex()

// TRUSTS edge suspicion_flag index (path traversal exclusion)
mgmt.buildIndex('trustsBySuspicionFlag', Edge.class).addKey(mgmt.getPropertyKey('suspicion_flag')).indexOnly(mgmt.getEdgeLabel('TRUSTS')).buildCompositeIndex()

// DISTRUSTS is_active index (moderator and query lookups)
mgmt.buildIndex('distrustsByIsActive', Edge.class).addKey(mgmt.getPropertyKey('is_active')).indexOnly(mgmt.getEdgeLabel('DISTRUSTS')).buildCompositeIndex()

// VOUCHES is_revoked index (active vouch queries)
mgmt.buildIndex('vouchesByIsRevoked', Edge.class).addKey(mgmt.getPropertyKey('is_revoked')).indexOnly(mgmt.getEdgeLabel('VOUCHES')).buildCompositeIndex()

// ========================================
// MIXED INDICES (Full-Text Search)
// ========================================

// Requires Elasticsearch backend
mgmt.buildIndex('userSearchIndex', Vertex.class).addKey(mgmt.getPropertyKey('name'), Mapping.TEXT.asParameter()).addKey(mgmt.getPropertyKey('domain_tags'), Mapping.STRING.asParameter()).indexOnly(mgmt.getVertexLabel('User')).buildMixedIndex('search')

mgmt.buildIndex('startupSearchIndex', Vertex.class).addKey(mgmt.getPropertyKey('name'), Mapping.TEXT.asParameter()).addKey(mgmt.getPropertyKey('domain'), Mapping.STRING.asParameter()).indexOnly(mgmt.getVertexLabel('Startup')).buildMixedIndex('search')

// User ranking index — enables range/sort queries on reputation and EigenTrust rank
mgmt.buildIndex('userRankingIndex', Vertex.class).addKey(mgmt.getPropertyKey('reputation_score'), Mapping.DEFAULT.asParameter()).addKey(mgmt.getPropertyKey('eigen_trust_rank'), Mapping.DEFAULT.asParameter()).indexOnly(mgmt.getVertexLabel('User')).buildMixedIndex('search')

// Commit schema
mgmt.commit()

// Wait for index to be available
ManagementSystem.awaitGraphIndexStatus(graph, 'userByUserId').call()
ManagementSystem.awaitGraphIndexStatus(graph, 'startupByStartupId').call()
ManagementSystem.awaitGraphIndexStatus(graph, 'orgByOrgId').call()
ManagementSystem.awaitGraphIndexStatus(graph, 'trustsByStatus').call()
ManagementSystem.awaitGraphIndexStatus(graph, 'trustsBySuspicionFlag').call()
ManagementSystem.awaitGraphIndexStatus(graph, 'distrustsByIsActive').call()
ManagementSystem.awaitGraphIndexStatus(graph, 'vouchesByIsRevoked').call()
ManagementSystem.awaitGraphIndexStatus(graph, 'userRankingIndex').call()

println("✅ Schema initialized successfully!")
"""

def main():
    """Print schema initialization script"""
    
    logger.info("=" * 70)
    logger.info("JanusGraph Schema Initialization Script")
    logger.info("=" * 70)
    logger.info("")
    logger.info("To initialize the schema, run the following commands:")
    logger.info("")
    logger.info("1. Connect to JanusGraph gremlin console:")
    logger.info("   docker-compose exec janusgraph bin/gremlin.sh")
    logger.info("")
    logger.info("2. Execute the following Groovy script:")
    logger.info("")
    logger.info(SCHEMA_SCRIPT)
    logger.info("")
    logger.info("=" * 70)
    
    # Alternative: Write to file
    with open('init_schema.groovy', 'w') as f:
        f.write(SCHEMA_SCRIPT)
    
    logger.info("✅ Schema script written to: init_schema.groovy")
    logger.info("")
    logger.info("To execute:")
    logger.info("   docker-compose exec janusgraph bin/gremlin.sh -e scripts/init_schema.groovy")

if __name__ == "__main__":
    main()
