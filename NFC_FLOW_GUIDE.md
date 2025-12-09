# 🎫 Grand Egyptian Museum - Hybrid NFC Access System Flow

## Overview
Users can enter the museum using **either** their smartphone (Virtual NFC via HCE) **OR** a physical souvenir card. Both IDs are **permanent and fixed** once set.

---

## 📱 Virtual NFC Flow (Mobile App)

### 1. **User Registration/First Login**
```
User opens app → Creates account/Logs in
         ↓
App generates unique virtual_nfc_id
  (e.g., "GEM_USER_12345" or UUID)
         ↓
App stores ID locally (secure storage)
         ↓
App calls: POST /api/nfc/register
  {
    "user_id": 123,
    "virtual_nfc_id": "GEM_USER_12345"
  }
         ↓
Backend saves to database
```

### 2. **Subsequent App Launches**
```
User opens app → App retrieves stored virtual_nfc_id
         ↓
No API call needed (ID is permanent)
         ↓
User approaches gate → NFC reader scans phone
         ↓
Gate calls: POST /api/gate/scan
  { "scanned_id": "GEM_USER_12345" }
         ↓
Backend: ACCESS_GRANTED ✅
```

### 📝 Mobile App Implementation Example (Kotlin/Android)
```kotlin
// First launch
val sharedPrefs = context.getSharedPreferences("gem_prefs", Context.MODE_PRIVATE)
var virtualNfcId = sharedPrefs.getString("virtual_nfc_id", null)

if (virtualNfcId == null) {
    // Generate once and save forever
    virtualNfcId = "GEM_USER_${userId}_${UUID.randomUUID()}"
    sharedPrefs.edit().putString("virtual_nfc_id", virtualNfcId).apply()
    
    // Register with backend
    api.registerVirtualNFC(userId, virtualNfcId)
}

// Configure HCE to broadcast this ID when scanned
```

---

## 🎴 Physical Card Flow

### 1. **Card Purchase/Distribution**
```
User buys souvenir card at museum shop
         ↓
Card has pre-printed UID (e.g., "04:A2:55:12:34:56:78")
         ↓
Staff/User links card to account:
  POST /api/cards/link
  {
    "user_id": 123,
    "card_uid": "04:A2:55:12:34:56:78"
  }
         ↓
Backend saves physical_card_id
```

### 2. **Using the Card**
```
User taps card at gate
         ↓
NFC reader reads card UID
         ↓
Gate calls: POST /api/gate/scan
  { "scanned_id": "04:A2:55:12:34:56:78" }
         ↓
Backend: ACCESS_GRANTED ✅
```

---

## 🚪 Gate Authentication Flow

```
NFC Reader detects ID (phone OR card)
         ↓
Gate system calls: POST /api/gate/scan
  { "scanned_id": "..." }
         ↓
Backend searches database:
  WHERE virtual_nfc_id = scanned_id
     OR physical_card_id = scanned_id
         ↓
┌─────────────────────────────────────┐
│  User Found?                        │
├─────────────────────────────────────┤
│  ✅ YES → Return ACCESS_GRANTED     │
│     + user name                     │
│     + welcome message               │
│                                     │
│  ❌ NO → Return ACCESS_DENIED       │
└─────────────────────────────────────┘
```

---

## 🔒 Important Design Decisions

### ✅ Both IDs are **PERMANENT**
- **virtual_nfc_id**: Generated once by app, never changes
- **physical_card_id**: Physical hardware UID, never changes
- This ensures consistent authentication across sessions

### ✅ Both IDs are **UNIQUE** (database constraints)
- One ID cannot be shared by multiple users
- Prevents security issues and conflicts

### ✅ Both IDs are **OPTIONAL**
- Users can have:
  - ✅ Only virtual NFC (phone users)
  - ✅ Only physical card (tourists who buy cards)
  - ✅ Both (full experience)
  - ❌ Neither (must register one to enter)

### ✅ IDs can be **RE-REGISTERED**
- The `/api/nfc/register` endpoint is **idempotent**
- Safe to call multiple times with same ID (no-op)
- Useful if user reinstalls app or needs to re-sync

---

## 🛠️ API Endpoints Summary

| Endpoint | Purpose | Called By | Frequency |
|----------|---------|-----------|-----------|
| `POST /api/nfc/register` | Register phone's virtual NFC ID | Mobile App | Once per app install |
| `POST /api/cards/link` | Link physical card to user | POS System / App | Once per card purchase |
| `POST /api/gate/scan` | Authenticate at gate | NFC Gate Reader | Every gate entry |

---

## 📊 Database Schema

```sql
CREATE TABLE visitor (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    virtual_nfc_id TEXT UNIQUE,      -- Phone HCE ID
    physical_card_id TEXT UNIQUE,    -- Card hardware UID
    INDEX(virtual_nfc_id),
    INDEX(physical_card_id)
);
```

---

## 🧪 Testing the System

### 1. Create a test user
```bash
curl -X POST "http://localhost:8000/visitors/" \
  -H "Content-Type: application/json" \
  -d '{"email": "tourist@example.com", "name": "Ahmed"}'
```

### 2. Register virtual NFC (simulating mobile app)
```bash
curl -X POST "http://localhost:8000/api/nfc/register" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "virtual_nfc_id": "GEM_USER_001"}'
```

### 3. Link physical card
```bash
curl -X POST "http://localhost:8000/api/cards/link" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "card_uid": "04:A2:55:12:34:56:78"}'
```

### 4. Test gate scan with phone ID
```bash
curl -X POST "http://localhost:8000/api/gate/scan" \
  -H "Content-Type: application/json" \
  -d '{"scanned_id": "GEM_USER_001"}'
```

### 5. Test gate scan with card ID
```bash
curl -X POST "http://localhost:8000/api/gate/scan" \
  -H "Content-Type: application/json" \
  -d '{"scanned_id": "04:A2:55:12:34:56:78"}'
```

Both should return `ACCESS_GRANTED` ✅

---

## 🎯 Summary

**Your Question**: Should NFC be generated at login?

**Answer**: 
- ✅ **YES** - The mobile app generates `virtual_nfc_id` on **first login**
- ✅ **FIXED** - Once generated, it's stored permanently in the app
- ✅ **Backend stores it** via `/api/nfc/register` endpoint
- ✅ **Physical cards** have pre-existing UIDs (hardware level)
- ✅ **Both are permanent** - no regeneration needed

This architecture ensures:
- Secure, consistent authentication
- Works offline after initial registration
- Supports multiple authentication methods
- Scalable for museum operations
