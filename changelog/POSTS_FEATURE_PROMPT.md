# Startup Posts Tab — Detailed Implementation Prompt

## Context & Constraints

You are extending the **TrustGraph** app — a Flutter + Python FastAPI microservices project.

**Existing stack:**
- Flutter frontend (`go_router` v13, `provider`, `dio`, `hive`, `image_picker`, bottom nav with 6 tabs: Home / Search / Connections / Messages / Intros / Profile)
- `api-gateway` FastAPI service (auth, JWT, proxies to downstream services)
- `graph-service` (JanusGraph via Gremlin — vertices: `User`, `Startup`; edges: `TRUSTS`, `FOUNDED`, `INVESTED_IN`, etc.)
- `messaging-service` (MongoDB-backed)
- `workflow-service` (intro workflows, Kafka consumers)
- Shared JWT auth in `backend/shared/auth/`

**Authorization rule for posts:** A user may create a post for a startup only if a `FOUNDED` edge (with `active=True`) exists from that user's `user_id` to the startup's `startup_id` in the graph service. All authenticated users (any role) can **read** posts. Unauthenticated requests must be rejected.

---

## Phase 1 — Backend: New `post-service`

Create a new microservice `backend/post-service/` following the **exact same Dockerfile + requirements layout** as `messaging-service`.

### 1.1 MongoDB Schema (`posts` collection)

Each document:
```json
{
  "_id": "<uuid>",
  "post_id": "<uuid>",
  "startup_id": "<string>",
  "startup_name": "<string>",
  "author_user_id": "<string>",
  "author_name": "<string>",
  "title": "<string, max 120 chars>",
  "body": "<string, max 2000 chars>",
  "tags": ["<string>"],
  "media_urls": ["<string>"],
  "visibility": "public",
  "like_count": 0,
  "comment_count": 0,
  "is_pinned": false,
  "is_deleted": false,
  "created_at": "<ISO datetime>",
  "updated_at": "<ISO datetime>"
}
```

### 1.2 Pydantic Schemas (`app/schemas/post_schemas.py`)

```python
class PostCreate(BaseModel):
    startup_id: str
    title: str = Field(..., min_length=3, max_length=120)
    body: str = Field(..., min_length=10, max_length=2000)
    tags: List[str] = Field(default_factory=list, max_length=10)
    media_urls: List[str] = Field(default_factory=list, max_length=5)

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=120)
    body: Optional[str] = Field(None, min_length=10, max_length=2000)
    tags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None

class PostResponse(BaseModel):
    post_id: str
    startup_id: str
    startup_name: str
    author_user_id: str
    author_name: str
    title: str
    body: str
    tags: List[str]
    media_urls: List[str]
    like_count: int
    comment_count: int
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

class PostFeedResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    page_size: int
```

### 1.3 API Routes (`app/api/posts.py`)

| Method | Path | Auth required | Who can call |
|---|---|---|---|
| `GET` | `/posts/feed?page=1&page_size=20&startup_id=&tag=` | Yes | Any authenticated user |
| `GET` | `/posts/{post_id}` | Yes | Any authenticated user |
| `POST` | `/posts/` | Yes | Founder with active FOUNDED edge to the startup |
| `PUT` | `/posts/{post_id}` | Yes | Original author only |
| `DELETE` | `/posts/{post_id}` | Yes | Original author only |
| `POST` | `/posts/{post_id}/like` | Yes | Any authenticated user |
| `DELETE` | `/posts/{post_id}/like` | Yes | Any authenticated user |

**Authorization flow for `POST /posts/`:**
1. Extract `user_id` from JWT (use `backend/shared/auth/dependencies.py` pattern).
2. Call `graph-service` internally: `GET /graph/vertices/users/{user_id}/startups/founded` — check the returned list contains `startup_id` with `active=True`.
3. If not found → raise `HTTP 403 Forbidden: "Only active founders of this startup can post updates"`.
4. Fetch `startup_name` from graph-service and `author_name` from the user vertex before inserting.

**`GET /posts/feed` query params:**
- `page` (int, default 1), `page_size` (int, default 20, max 50)
- `startup_id` (optional filter)
- `tag` (optional filter)
- Sort: `created_at` descending

Never return documents where `is_deleted = True`.

### 1.4 Like System (`post_likes` collection)

```json
{ "post_id": "<string>", "user_id": "<string>", "created_at": "<datetime>" }
```
Unique compound index on `(post_id, user_id)`. On `POST /like` increment `like_count` atomically. On `DELETE /like` decrement (floor 0).

### 1.5 Service Registration in `docker-compose.yml`

Add a `post-service` container:
- Image built from `backend/post-service/Dockerfile`
- Env vars: `MONGO_URL`, `JWT_SECRET_KEY`, `GRAPH_SERVICE_URL`, `LOG_LEVEL`
- Port `8005:8005`
- Depends on: `mongodb`, `graph-service`

### 1.6 API Gateway Proxy (`backend/api-gateway/app/api/posts.py`)

Add a wildcard proxy route that forwards `POST /api/posts/{path}` to `http://post-service:8005`. Follow the same pattern already used for messaging (use `httpx.AsyncClient`). Mount under prefix `/api/posts`. Attach JWT auth middleware so the gateway validates the token before forwarding.

---

## Phase 2 — Backend: Graph Service Extension

Add one new read-only endpoint to `graph-service` (`backend/graph-service/app/api/vertices.py`):

```
GET /graph/vertices/users/{user_id}/startups/founded
```

Returns a list of `{ startup_id, name, stage, domain }` for all startups where an active `FOUNDED` edge exists from this user. This is used by the post-service for authorization.

---

## Phase 3 — Flutter Frontend

### 3.1 Folder structure

```
lib/features/posts/
  data/
    models/post_model.dart
    repositories/post_repository.dart
  services/
    post_provider.dart          # ChangeNotifier
  screens/
    posts_feed_screen.dart      # public feed (tab shown to all users)
    create_post_screen.dart     # only founders see the FAB that opens this
    post_detail_screen.dart     # full post view with body + comments stub
  widgets/
    post_card.dart
    startup_selector_dropdown.dart
    tag_input_field.dart
    like_button.dart
```

### 3.2 `PostModel` (`data/models/post_model.dart`)

Mirror all fields from `PostResponse` schema above. Add a `fromJson` factory and `toJson` method. Include `bool isLikedByCurrentUser = false` as a transient field (not from server, managed by provider).

### 3.3 `PostRepository` (`data/repositories/post_repository.dart`)

Uses the existing `ApiClient` (Dio). Methods:
```dart
Future<List<PostModel>> getFeed({int page = 1, int pageSize = 20, String? startupId, String? tag});
Future<PostModel> getPost(String postId);
Future<PostModel> createPost({required String startupId, required String title, required String body, List<String> tags = const [], List<String> mediaUrls = const []});
Future<PostModel> updatePost(String postId, {String? title, String? body, List<String>? tags});
Future<void> deletePost(String postId);
Future<void> likePost(String postId);
Future<void> unlikePost(String postId);
Future<List<Map<String, dynamic>>> getFoundedStartups();  // calls graph-service via gateway
```

**Error handling:** Wrap all Dio calls in try/catch; rethrow `DioException` as domain-level `AppException` (follow same pattern used in `connection_repository.dart`).

### 3.4 `PostProvider` (`services/post_provider.dart`)

`ChangeNotifier` with state:
```dart
List<PostModel> _posts = [];
bool _isLoading = false;
bool _hasMore = true;
int _currentPage = 1;
String? _error;
String? _activeStartupFilter;
String? _activeTagFilter;
```

Methods: `loadFeed(refresh: bool)`, `loadMore()`, `createPost(...)`, `deletePost(String id)`, `toggleLike(String postId)`. Call `notifyListeners()` after every state change. Use `_currentPage` for pagination — append new posts on `loadMore()`, replace on refresh.

Register in `app.dart` alongside `MessagingProvider`:
```dart
ChangeNotifierProvider(create: (_) => PostProvider(PostRepository(_apiClient))),
```

### 3.5 `PostsFeedScreen` (`screens/posts_feed_screen.dart`)

- `StatefulWidget`, consumes `PostProvider` via `context.watch<PostProvider>()`.
- `AppBar` with title `"Startup Updates"`, filter icon (opens bottom sheet with startup/tag filters).
- Body: `ListView.builder` with `PostCard` widgets. On scroll to bottom call `provider.loadMore()`. Show `CircularProgressIndicator` at list bottom while loading more.
- Pull-to-refresh using `RefreshIndicator` → calls `provider.loadFeed(refresh: true)`.
- **Role-gated FAB**: read `currentUser.rolePrimary` from `AuthRepository`; if `'founder'`, show a `FloatingActionButton` with `Icons.add` that navigates to `/posts/create`. Non-founders see no FAB.
- Empty state widget: centered icon + `"No updates yet"` text.
- Error state: retry button.

### 3.6 `PostCard` widget (`widgets/post_card.dart`)

```
┌──────────────────────────────────────────┐
│ [Startup Logo placeholder]  StartupName  │
│ author_name · time ago                    │
├──────────────────────────────────────────┤
│ **Title** (bold, 1 line overflow ellipsis)│
│ body preview (3 lines max, overflow ...)  │
│ [tag chip] [tag chip]                     │
│                                           │
│ [media thumbnail row if media_urls ≠ []] │
│                                           │
│ ♥ 12   💬 3          [•••] overflow menu │
└──────────────────────────────────────────┘
```

- Tap card → `context.push('/posts/${post.postId}')`.
- `LikeButton` widget: animated heart toggle, calls `provider.toggleLike(post.postId)` optimistically.
- Overflow menu (`PopupMenuButton`): show `"Edit"` and `"Delete"` only if `post.authorUserId == currentUserId`. Delete shows a `showDialog` confirm before calling `provider.deletePost`.
- Use `timeago` package (add to `pubspec.yaml`) for relative timestamps.

### 3.7 `CreatePostScreen` (`screens/create_post_screen.dart`)

- `StatefulWidget` with a `Form` using `GlobalKey<FormState>`.
- Fields:
  1. **Startup selector** (`StartupSelectorDropdown`) — populated from `PostRepository.getFoundedStartups()`, shows `DropdownButtonFormField<String>`. Validates non-null selection.
  2. **Title** `TextFormField` — max 120 chars, shows char counter.
  3. **Body** `TextFormField` — multiline, max 2000 chars, min 3 lines, shows char counter.
  4. **Tags** `TagInputField` — user types a tag and presses Enter/comma; renders as `Chip` list below the input, max 10 tags, each max 30 chars.
  5. **Media** — `IconButton` with `Icons.image` triggers `image_picker`; selected images shown as horizontal scrollable thumbnail row (max 5). Uploads to `POST /posts/media/upload` (a separate endpoint that returns a URL — implement this endpoint too using local filesystem storage in the container or an env-configured S3 URL prefix).
- Submit button `"Publish Update"` — shows `CircularProgressIndicator` while in-flight, disabled while loading.
- On success: `Navigator.pop(context)` and call `provider.loadFeed(refresh: true)`.
- On error: show `SnackBar` with the error message.
- Validation rules enforced client-side: title ≥ 3 chars, body ≥ 10 chars, startup must be selected.

### 3.8 `PostDetailScreen` (`screens/post_detail_screen.dart`)

- Shows full post body, all tags, full-size media (horizontal `PageView`).
- Like button in the `AppBar` actions.
- Scrollable `Column`: post header → full body → tags → comments placeholder section (`"Comments coming soon"` stub card).
- If `authorUserId == currentUserId`: show edit/delete in `AppBar` actions.

### 3.9 Routing additions (`core/routing/app_router.dart`)

```dart
GoRoute(path: '/posts', name: 'posts', builder: (_, __) => const PostsFeedScreen()),
GoRoute(path: '/posts/create', name: 'create-post', builder: (_, __) => const CreatePostScreen()),
GoRoute(
  path: '/posts/:postId',
  name: 'post-detail',
  builder: (_, state) => PostDetailScreen(postId: state.pathParameters['postId']!),
),
```

### 3.10 Bottom Navigation update (`home_screen.dart`)

Insert the **Posts** tab at index **2** (between Search and Connections). Shift all existing indices up by 1. The new destination:

```dart
NavigationDestination(
  icon: Icon(Icons.article_outlined),
  selectedIcon: Icon(Icons.article),
  label: 'Posts',
),
```

Update all `case` branches in `onDestinationSelected` accordingly. The `PostsFeedScreen` itself is navigated to via `context.go('/posts')`.

---

## Phase 4 — Security & Validation Checklist

| # | Check | Where |
|---|---|---|
| 1 | JWT required on every post-service endpoint; validate signature using shared secret | API Gateway + post-service `dependencies.py` |
| 2 | Founder authorization: verify FOUNDED edge server-side — never trust client-supplied `startup_id` alone | `POST /posts/` handler |
| 3 | Author-only writes: `PUT` and `DELETE` compare `post.author_user_id == current_user_id` | post-service route handlers |
| 4 | Input length limits enforced on both Pydantic (backend) and `TextFormField` `maxLength` (frontend) | schemas + Flutter form |
| 5 | `media_urls` must be validated against allowed URL prefix or domain — never store arbitrary URLs from client | `PostCreate` validator |
| 6 | MongoDB `is_deleted` soft-delete: never expose deleted posts in any query | All `GET` queries add `{"is_deleted": False}` filter |
| 7 | Pagination: enforce `page_size` max 50 server-side to prevent data dumps | Feed route query params |
| 8 | Rate limiting on create: max 10 posts per founder per 24h (use Redis counter key `post_rate:{user_id}` with 86400s TTL) | `POST /posts/` handler |

---

## Phase 5 — `pubspec.yaml` additions

```yaml
timeago: ^3.6.0               # relative timestamps on post cards
cached_network_image: ^3.3.1  # lazy-load media thumbnails
```

---

## Summary of all new files

### Backend
| File | Action |
|---|---|
| `backend/post-service/Dockerfile` | Create |
| `backend/post-service/requirements.txt` | Create |
| `backend/post-service/app/main.py` | Create |
| `backend/post-service/app/core/config.py` | Create |
| `backend/post-service/app/core/database.py` | Create |
| `backend/post-service/app/schemas/post_schemas.py` | Create |
| `backend/post-service/app/api/posts.py` | Create |
| `backend/post-service/app/services/post_service.py` | Create |
| `backend/api-gateway/app/api/posts.py` | Create (new proxy router) |
| `backend/api-gateway/app/main.py` | Modify (include posts router) |
| `backend/graph-service/app/api/vertices.py` | Modify (add `/founded` endpoint) |
| `docker-compose.yml` | Modify (add `post-service`) |

### Frontend
| File | Action |
|---|---|
| `lib/features/posts/data/models/post_model.dart` | Create |
| `lib/features/posts/data/repositories/post_repository.dart` | Create |
| `lib/features/posts/services/post_provider.dart` | Create |
| `lib/features/posts/screens/posts_feed_screen.dart` | Create |
| `lib/features/posts/screens/create_post_screen.dart` | Create |
| `lib/features/posts/screens/post_detail_screen.dart` | Create |
| `lib/features/posts/widgets/post_card.dart` | Create |
| `lib/features/posts/widgets/startup_selector_dropdown.dart` | Create |
| `lib/features/posts/widgets/tag_input_field.dart` | Create |
| `lib/features/posts/widgets/like_button.dart` | Create |
| `lib/app.dart` | Modify (register `PostProvider`) |
| `lib/core/routing/app_router.dart` | Modify (3 new routes) |
| `lib/features/home/screens/home_screen.dart` | Modify (Posts tab at index 2, shift indices) |
| `pubspec.yaml` | Modify (`timeago`, `cached_network_image`) |
