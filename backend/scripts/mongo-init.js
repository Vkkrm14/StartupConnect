// MongoDB initialization script
// This runs when MongoDB container first starts

db = db.getSiblingDB('trustgraph_db');

// Create collections
db.createCollection('users');
db.createCollection('intro_requests');
db.createCollection('approvals');
db.createCollection('posts');
db.createCollection('verification_documents');

// Create indices for users
db.users.createIndex({ "user_id": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true, sparse: true });
db.users.createIndex({ "role_primary": 1 });
db.users.createIndex({ "geography": 1 });

// Create indices for intro_requests
db.intro_requests.createIndex({ "intro_id": 1 }, { unique: true });
db.intro_requests.createIndex({ "requester_id": 1 });
db.intro_requests.createIndex({ "founder_id": 1 });
db.intro_requests.createIndex({ "investor_id": 1 });
db.intro_requests.createIndex({ "status": 1 });
db.intro_requests.createIndex({ "created_at": -1 });
db.intro_requests.createIndex({ "path_nodes": 1 });

// Create indices for posts
db.posts.createIndex({ "post_id": 1 }, { unique: true });
db.posts.createIndex({ "author_id": 1 });
db.posts.createIndex({ "post_type": 1 });
db.posts.createIndex({ "visibility_scope": 1 });
db.posts.createIndex({ "created_at": -1 });
db.posts.createIndex({ "domain_tags": 1 });

print('✅ MongoDB initialized successfully for TrustGraph!');
