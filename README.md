# 🏛️ Grand Egyptian Museum - Smart Backend System

A FastAPI-based backend for the Grand Egyptian Museum featuring:
- **Hybrid NFC Access System** (Phone HCE + Physical Cards)
- **Photography Competition** with real-time leaderboards
- **Visitor Management**

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip or uv package manager

### Installation & Run

```bash
# Install dependencies
pip install fastapi "uvicorn[standard]" sqlmodel python-multipart

# Initialize database with NFC fields
python migrate_db.py

# Start the server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at:
- API: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs`

## 🎫 NFC Access System

### Features
- 📱 **Virtual NFC**: Users authenticate via phone (HCE)
- 🎴 **Physical Cards**: Souvenir cards with pre-printed UIDs
- 🔄 **Hybrid Support**: Users can have one or both methods
- 🔒 **Secure**: Unique, indexed, permanent IDs

### API Endpoints

#### 1. Register Virtual NFC (Mobile App)
```http
POST /api/nfc/register
Content-Type: application/json

{
  "user_id": 1,
  "virtual_nfc_id": "GEM_USER_001"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Virtual NFC ID registered for user Ahmed",
  "user_id": 1,
  "virtual_nfc_id": "GEM_USER_001"
}
```

#### 2. Link Physical Card
```http
POST /api/cards/link
Content-Type: application/json

{
  "user_id": 1,
  "card_uid": "04:A2:55:12:34:56:78"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Physical card successfully linked to user Ahmed",
  "user_id": 1,
  "card_uid": "04:A2:55:12:34:56:78"
}
```

#### 3. Gate Authentication
```http
POST /api/gate/scan
Content-Type: application/json

{
  "scanned_id": "GEM_USER_001"
}
```

**Response (Access Granted):**
```json
{
  "status": "ACCESS_GRANTED",
  "user_name": "Ahmed",
  "welcome_message": "Welcome back, Ahmed!"
}
```

**Response (Access Denied):**
```json
{
  "status": "ACCESS_DENIED"
}
```

## 📸 Photography Competition

### Endpoints

#### Upload Photo
```http
POST /upload-photo/
Content-Type: multipart/form-data

visitor_id: 1
room_id: 2
file: [image file]
```

#### Get Room Leaderboard
```http
GET /rooms/{room_id}/dashboard
```

Returns top 3 photos from the last hour.

## 👥 Visitor Management

#### Create Visitor
```http
POST /visitors/
Content-Type: application/json

{
  "email": "tourist@gem.eg",
  "name": "Ahmed",
  "gender": "male"
}
```

#### List All Visitors
```http
GET /visitors/
```

## 🗄️ Database Schema

### Visitor Model
```python
class Visitor(SQLModel, table=True):
    id: Optional[int]
    email: str (unique, required)
    name: Optional[str]
    gender: Optional[str]
    joined_at: datetime
    virtual_nfc_id: Optional[str] (unique, indexed)  # Phone HCE
    physical_card_id: Optional[str] (unique, indexed) # Souvenir card
```

### Other Models
- `Room`: Museum exhibition spaces
- `PhotoSubmission`: Photo competition entries
- `Badge`: Achievement badges
- `VisitorBadge`: Badge ownership (many-to-many)

## 📁 Project Structure

```
GEM-hackathon-backend/
├── main.py              # FastAPI app with all endpoints
├── database.py          # SQLModel schemas & DB setup
├── migrate_db.py        # Database migration script
├── NFC_FLOW_GUIDE.md    # Detailed NFC implementation guide
├── museum_system.db     # SQLite database (auto-generated)
├── static/
│   └── submissions/     # Uploaded photos
└── pyproject.toml       # Project dependencies
```

## 🧪 Testing

### Create Test User
```bash
curl -X POST "http://localhost:8000/visitors/" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@gem.eg", "name": "Test User"}'
```

### Register Virtual NFC
```bash
curl -X POST "http://localhost:8000/api/nfc/register" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "virtual_nfc_id": "GEM_USER_001"}'
```

### Link Physical Card
```bash
curl -X POST "http://localhost:8000/api/cards/link" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "card_uid": "04:A2:55:12:34:56:78"}'
```

### Test Gate Scan
```bash
# Test with virtual NFC
curl -X POST "http://localhost:8000/api/gate/scan" \
  -H "Content-Type: application/json" \
  -d '{"scanned_id": "GEM_USER_001"}'

# Test with physical card
curl -X POST "http://localhost:8000/api/gate/scan" \
  -H "Content-Type: application/json" \
  -d '{"scanned_id": "04:A2:55:12:34:56:78"}'
```

Both should return `ACCESS_GRANTED` ✅

## 🔒 Security Features

- ✅ Unique NFC IDs (database constraints)
- ✅ Duplicate card detection
- ✅ Indexed queries for fast lookups
- ✅ Permanent, non-regenerating IDs
- ✅ SQL injection protection (SQLModel/SQLAlchemy)

## 📚 Documentation

- **NFC Flow Guide**: See `NFC_FLOW_GUIDE.md` for detailed implementation
- **API Docs**: Visit `/docs` when server is running
- **Alternative Docs**: Visit `/redoc` for ReDoc interface

## 🛠️ Tech Stack

- **FastAPI**: Modern Python web framework
- **SQLModel**: SQL databases in Python with type safety
- **SQLite**: Lightweight database
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

## 📝 License

MIT License - Grand Egyptian Museum Hackathon 2025
