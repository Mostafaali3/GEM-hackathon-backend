import os
import shutil
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, desc

# Import the tables and engine from your existing database.py file
from database import Visitor, Room, PhotoSubmission, engine, create_db_and_tables

# 1. APP SETUP
# ------------
app = FastAPI(title="Museum Smart System")

# Create a folder for uploaded images
IMAGEDIR = "static/submissions/"
os.makedirs(IMAGEDIR, exist_ok=True)

# Mount the static folder so the frontend can display the images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Helper to get the database session
def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# 2. VISITOR ENDPOINTS
# --------------------
@app.post("/visitors/", response_model=Visitor)
def create_visitor(visitor: Visitor, session: Session = Depends(get_session)):
    """Register a new visitor (only email is strictly required)."""
    session.add(visitor)
    session.commit()
    session.refresh(visitor)
    return visitor

@app.get("/visitors/", response_model=List[Visitor])
def list_visitors(session: Session = Depends(get_session)):
    return session.exec(select(Visitor)).all()

# 3. PHOTOGRAPHY COMPETITION ENDPOINTS
# ------------------------------------
@app.post("/upload-photo/")
def upload_photo(
    visitor_id: int = Form(...),
    room_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    Visitor uploads a photo for a specific room.
    1. Saves image to disk.
    2. Creates database entry linked to Visitor and Room.
    """
    # A. Validate Visitor and Room exist
    if not session.get(Visitor, visitor_id):
        raise HTTPException(status_code=404, detail="Visitor not found")
    if not session.get(Room, room_id):
        raise HTTPException(status_code=404, detail="Room not found")

    # B. Save file to disk with unique name
    file_extension = file.filename.split(".")[-1]
    filename = f"{uuid4()}.{file_extension}"
    file_path = os.path.join(IMAGEDIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # C. Save to Database
    # Note: We create a random score between 1-100 just for the demo 
    # so you can test the "Winner" logic immediately.
    import random
    demo_score = random.randint(10, 100) 

    photo = PhotoSubmission(
        visitor_id=visitor_id,
        room_id=room_id,
        image_url=f"/static/submissions/{filename}",
        score=demo_score 
    )
    
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return {"status": "success", "photo": photo}

@app.get("/rooms/{room_id}/dashboard", response_model=List[PhotoSubmission])
def get_room_dashboard(room_id: int, session: Session = Depends(get_session)):
    """
    Returns the Top 3 photos for this room uploaded in the last hour.
    """
    # Calculate time 1 hour ago
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # Logic: Select Photos -> Where Room matches -> Where time > 1 hour ago -> Order by Score -> Top 3
    statement = (
        select(PhotoSubmission)
        .where(PhotoSubmission.room_id == room_id)
        .where(PhotoSubmission.created_at >= one_hour_ago)
        .order_by(desc(PhotoSubmission.score))
        .limit(3)
    )
    
    results = session.exec(statement).all()
    return results  