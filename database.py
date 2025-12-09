from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, create_engine, Session, select

# --- 1. THE TABLES ---

class Visitor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True) # The only required field
    name: Optional[str] = None
    gender: Optional[str] = None 
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Hybrid NFC Access System Fields
    virtual_nfc_id: Optional[str] = Field(default=None, unique=True, index=True)  # Phone HCE ID (e.g., 'GEM_USER_001')
    physical_card_id: Optional[str] = Field(default=None, unique=True, index=True)  # Souvenir Card UID (e.g., '04:A2:55...')

class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # e.g., "Main Hall", "Dinosaur Exhibit"
    description: Optional[str] = None

class PhotoSubmission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_url: str  # Path to the file on disk
    
    # Relationships
    visitor_id: int = Field(foreign_key="visitor.id")
    room_id: int = Field(foreign_key="room.id")
    
    # Competition Logic
    created_at: datetime = Field(default_factory=datetime.utcnow) # Crucial for "Best of the Hour"
    score: int = Field(default=0)  # Logic to determine the "best" (could be admin votes)
    is_hourly_winner: bool = Field(default=False) # Flag to mark if this photo won the prize

class Badge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str # e.g., "Photography Pro", "Early Bird"
    icon_url: Optional[str] = None # Path to badge image

# This table links Visitors to Badges (Many-to-Many)
class VisitorBadge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    visitor_id: int = Field(foreign_key="visitor.id")
    badge_id: int = Field(foreign_key="badge.id")
    earned_at: datetime = Field(default_factory=datetime.utcnow)

# --- 2. SETUP ENGINE ---

sqlite_file_name = "museum_system.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# --- 3. RUN ---
if __name__ == "__main__":
    create_db_and_tables()
    
    # Let's Seed (Create) some dummy Rooms so the system isn't empty
    with Session(engine) as session:
        # Check if rooms exist, if not, add them
        existing_rooms = session.exec(select(Room)).first()
        if not existing_rooms:
            room1 = Room(name="Ancient Egypt Gallery")
            room2 = Room(name="Royal Mummies Hall")
            room3 = Room(name="Grand Entrance")
            session.add(room1)
            session.add(room2)
            session.add(room3)
            session.commit()
            print("Database created and generic Rooms added!")
        else:
            print("Database created (Rooms already exist).")