# 🧪 Flutter App Testing Guide

## ✅ App Status: RUNNING

Your Flutter app is now running in Chrome!

**DevTools URL:** http://127.0.0.1:9101?uri=http://127.0.0.1:64963/NDvt2rI6noU=

---

## 📱 App Structure

### Implemented Features:
- ✅ **Authentication Screens**: Login & Register (mock authentication)
- ✅ **Home Screen**: Dashboard with trust score and activity feed
- ✅ **Search Screen**: Find users and startups
- ✅ **Intro Request Screen**: Request introductions with multi-hop path discovery
- ✅ **Profile Screens**: User profile, edit profile, connections
- ✅ **Intro Management**: Pending intros, my requests, intro details

### Backend Integration:
- ✅ **API Client**: Dio-based with JWT token management
- ✅ **Path Discovery**: Integrated with Graph Service
- ✅ **Intro Repository**: Workflow service integration
- ✅ **Search Integration**: Search service ready

---

## 🧪 Manual Testing Steps

### 1. **Login Screen** (Current Screen)
- Should see the TrustGraph logo and login form
- Email and password fields present
- "Login" button visible

**Action:** Since auth is mocked, just enter any email/password and click Login

---

### 2. **Home Screen** (After Login)
- Should show navigation bar at bottom (Home, Search, Intros, Profile)
- Trust score card displayed
- Activity feed visible
- Search FAB (Floating Action Button) in bottom right

**Test:** Navigate between tabs using bottom navigation

---

### 3. **Search Screen**
**Path:** Tap "Search" in bottom navigation

**Expected:**
- Search bar at top
- User and startup search tabs
- Search results display

**Test API Connection:**
- Type a search query
- Check browser DevTools Console (F12) for API calls
- Should attempt to call: `http://localhost:8000/api/v1/search/users`

---

### 4. **Path Discovery (Main Feature!)**

**Setup Required:**
Since auth is mocked, you need to manually set a user ID for testing.

**Option A: Quick Test with Mock Data**
1. Open Browser DevTools (F12) → Console
2. Set a test user ID:
   ```javascript
   localStorage.setItem('user_id', '645271ec-...');  // Alice's ID from seed data
   ```

**Option B: Test with Real Seeded Data**

From our earlier test, we have these users:
- **Alice Johnson** (founder): `645271ec-...`
- **Ivy Martinez** (connector): ID from database
- **Frank Miller** (investor): `d83acffa-...`

**Testing Path Discovery:**
1. Go to Search or Profile
2. Click on a user (investor)
3. Click "Request Introduction"
4. Should call: `POST http://localhost:8000/api/v1/paths/discover`
5. Should display 2-4 hop paths with:
   - Route visualization
   - Trust scores
   - Path score
   - Success probability

---

### 5. **Check API Integration**

**Open Browser DevTools (F12) → Console & Network tabs**

Look for these API calls:
- ✅ `GET http://localhost:8000/health` → Should return all services healthy
- ⚠️ `POST http://localhost:8000/api/v1/paths/discover` → Path discovery
- ⚠️ `GET http://localhost:8000/api/v1/search/users` → User search

**Expected Issues:**
- ❌ **CORS errors**: Normal on first run (backend needs to allow Chrome origin)
- ❌ **Auth errors**: Expected (no real authentication implemented yet)
- ❌ **404 errors**: Some endpoints might not exist in API Gateway

---

## 🐛 Known Limitations

1. **Authentication**: Currently mocked (no real JWT)
2. **User Session**: No persistent login (use DevTools localStorage to set user_id)
3. **API Gateway CORS**: May need to add Chrome dev server to CORS origins
4. **Missing Screens**: Some profile/intro screens may be placeholders

---

## 🔧 Testing Backend Connection

### Quick Health Check:
```powershell
# From project root
Invoke-WebRequest -Uri "http://localhost:8000/health" | ConvertFrom-Json | ConvertTo-Json
```

### Test Path Discovery Directly:
```powershell
$body = @{
    founder_id = "645271ec-..."  # Alice
    investor_id = "d83acffa-..."  # Frank
    max_paths = 5
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/v1/paths/discover" `
    -Method POST `
    -Body $body `
    -ContentType "application/json" | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

## 🎯 What to Test

### Priority 1: Core Path Discovery
- [ ] Can navigate to intro request screen
- [ ] Path discovery API is called
- [ ] Multi-hop paths are displayed
- [ ] Path scores and explanations show correctly

### Priority 2: UI/UX
- [ ] Navigation works smoothly
- [ ] Screens load without errors
- [ ] Design is responsive
- [ ] Loading states work

### Priority 3: API Integration
- [ ] Health check succeeds
- [ ] Search API calls work
- [ ] Path discovery returns data
- [ ] Error handling displays nicely

---

## 🚀 Next Steps Based on Results

**If everything works:**
→ Enhance UI with better visualizations
→ Add real authentication
→ Implement state management for user session

**If CORS errors:**
→ Update backend CORS to allow Flutter dev server

**If path discovery fails:**
→ Check API Gateway proxy configuration
→ Verify Graph Service is accessible

**If UI issues:**
→ Fix responsive design
→ Enhance path visualization

---

## 📊 Current Seeded Data

From `backend/scripts/seed_data.py`:

**Founders:**
- Alice Johnson (fintech, saas) - San Francisco
- Bob Smith (healthtech, ai-ml) - New York
- Carol Davis (e-commerce, saas) - Austin
- David Lee (fintech, blockchain) - San Francisco
- Emma Wilson (ai-ml, edtech) - Boston

**Investors:**
- Frank Miller (fintech, saas) - Palo Alto
- Grace Chen (healthtech, ai-ml) - San Francisco
- Henry Brown (e-commerce, blockchain) - New York

**Connectors:**
- Ivy Martinez (fintech, saas) - San Francisco
- Jack Taylor (healthtech, ai-ml) - Boston

**Trust Paths:**
- Alice → Ivy (0.85) → Frank (0.90) ✅
- Alice → Ivy → Grace ✅
- Bob → Jack (0.80) → Grace (0.88) ✅
- Carol → Ivy → Frank ✅

---

## 🎉 Success Criteria

✅ **App loads in Chrome without crashes**
✅ **Can navigate between screens**
✅ **API calls are being made (check Network tab)**
✅ **Path discovery endpoint is being called**
✅ **Multi-hop paths are displayed when API succeeds**

---

## 📝 Notes

- Press `R` in the terminal to hot reload if you make changes
- Press `q` to quit the app
- Check `http://localhost:9101` for Flutter DevTools
- Backend services must be running (already verified ✅)

Time to test! 🚀
