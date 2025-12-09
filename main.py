import os
import shutil
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, desc, or_
from pydantic import BaseModel

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import the tables and engine from your existing database.py file
from database import Visitor, Room, PhotoSubmission, engine, create_db_and_tables
# LangChain Imports
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# Configuration
CHROMA_PATH = "./chroma_db"
OLLAMA_MODEL = "deepseek-v3.1.671b-cloud" # Make sure to pull this model: `ollama pull llama3`

# Global variable to hold the chain
rag_chain = None
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database (Moved from on_startup)
    create_db_and_tables()
    
    global rag_chain
    
    # 2. Initialize Embeddings
    print("Loading Embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

    # 3. Load existing VectorDB
    if not os.path.exists(CHROMA_PATH):
        # Graceful handling if DB doesn't exist yet
        print("⚠️ Warning: Chroma DB not found. RAG will not work until ingest.py is run.")
    else:
        vector_db = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings
        )

        # 4. Initialize LLM
        llm = ChatOllama(model="deepseek-v3.1:671b-cloud", temperature=0.2)

        # 5. Create RAG Chain
        retriever = vector_db.as_retriever(search_kwargs={"k": 5})
        
        template = """
        You are a helpful assistant. Use ONLY the context below to answer the question.
        If the answer is not in the context, say "I don't know."
        
        just give the answer as it will be shown to the user
        
        Context:
        {context}
        
        Question:
        {question}
        
        Answer:
        """
        
        prompt = PromptTemplate.from_template(template)
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        print("✅ RAG Pipeline loaded successfully.")
    
    yield
    # (Optional) Clean up resources on shutdown
    print("🛑 Server shutting down.")

# --- CONNECT LIFESPAN TO APP HERE ---
app = FastAPI(title="Museum Smart System", lifespan=lifespan)

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
    # Check if user with this email already exists
    existing_user = session.exec(select(Visitor).where(Visitor.email == visitor.email)).first()
    if existing_user:
        # Return existing user instead of creating duplicate
        return existing_user
    
    session.add(visitor)
    session.commit()
    session.refresh(visitor)
    return visitor

@app.get("/visitors/", response_model=List[Visitor])
def list_visitors(session: Session = Depends(get_session)):
    return session.exec(select(Visitor)).all()


@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    if not rag_chain:
        raise HTTPException(status_code=500, detail="RAG chain not initialized")
    
    try:
        # Invoke the chain
        response_text = rag_chain.invoke(request.question)
        return QueryResponse(answer=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
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

# 4. NFC ACCESS SYSTEM ENDPOINTS
# -------------------------------

# Request/Response Models
class RegisterVirtualNFCRequest(BaseModel):
    user_id: int
    virtual_nfc_id: str  # Generated by mobile app (e.g., 'GEM_USER_001' or UUID)

class RegisterVirtualNFCResponse(BaseModel):
    status: str
    message: str
    user_id: int
    virtual_nfc_id: str

class LoginRegisterRequest(BaseModel):
    email: str
    name: Optional[str] = None
    gender: Optional[str] = None
    virtual_nfc_id: str

class LoginRegisterResponse(BaseModel):
    status: str
    message: str
    user: Visitor
    is_new_user: bool

class LinkCardRequest(BaseModel):
    user_id: int
    card_uid: str

class LinkCardResponse(BaseModel):
    status: str
    message: str
    user_id: int
    card_uid: str

class GateScanRequest(BaseModel):
    scanned_id: str

class GateScanResponse(BaseModel):
    status: str
    user_name: Optional[str] = None
    welcome_message: Optional[str] = None
    


@app.post("/api/auth/login-register", response_model=LoginRegisterResponse)
def login_or_register(
    request: LoginRegisterRequest,
    session: Session = Depends(get_session)
):
    """
    Combined login/register endpoint for mobile app.
    
    - If user exists: Update their virtual_nfc_id and return user data
    - If user doesn't exist: Create new user with virtual_nfc_id
    
    This is the PRIMARY endpoint mobile apps should call on login.
    """
    # Check if user exists
    existing_user = session.exec(
        select(Visitor).where(Visitor.email == request.email)
    ).first()
    
    if existing_user:
        # User exists - update their virtual NFC ID
        existing_user.virtual_nfc_id = request.virtual_nfc_id
        if request.name:
            existing_user.name = request.name
        if request.gender:
            existing_user.gender = request.gender
        
        session.add(existing_user)
        session.commit()
        session.refresh(existing_user)
        
        return LoginRegisterResponse(
            status="success",
            message="Login successful",
            user=existing_user,
            is_new_user=False
        )
    else:
        # Create new user with virtual NFC ID
        new_user = Visitor(
            email=request.email,
            name=request.name,
            gender=request.gender,
            virtual_nfc_id=request.virtual_nfc_id
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        return LoginRegisterResponse(
            status="success",
            message="Account created successfully",
            user=new_user,
            is_new_user=True
        )

@app.post("/api/nfc/register", response_model=RegisterVirtualNFCResponse)
def register_virtual_nfc(
    request: RegisterVirtualNFCRequest,
    session: Session = Depends(get_session)
):
    """
    Register or update a user's virtual NFC ID from their mobile app.
    
    NOTE: Mobile apps should use POST /api/auth/login-register instead.
    This endpoint is kept for backward compatibility and manual NFC ID updates.
    """
    # A. Validate user exists
    user = session.get(Visitor, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {request.user_id} not found")
    
    # B. Check if this virtual_nfc_id is already taken by another user
    existing_nfc = session.exec(
        select(Visitor).where(Visitor.virtual_nfc_id == request.virtual_nfc_id)
    ).first()
    
    if existing_nfc and existing_nfc.id != request.user_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Virtual NFC ID '{request.virtual_nfc_id}' is already registered to another user (ID: {existing_nfc.id})"
        )
    
    # C. Update or set the user's virtual NFC ID (idempotent - safe to call multiple times)
    user.virtual_nfc_id = request.virtual_nfc_id
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return RegisterVirtualNFCResponse(
        status="success",
        message=f"Virtual NFC ID registered for user {user.name or user.email}",
        user_id=user.id,
        virtual_nfc_id=request.virtual_nfc_id
    )

@app.post("/api/cards/link", response_model=LinkCardResponse)
def link_physical_card(
    request: LinkCardRequest,
    session: Session = Depends(get_session)
):
    """
    Link a physical souvenir card to a user.
    
    - Finds the user by user_id
    - Updates their physical_card_id
    - Returns 400 if card is already linked to another user
    """
    # A. Validate user exists
    user = session.get(Visitor, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {request.user_id} not found")
    
    # B. Check if this card is already linked to another user
    existing_card = session.exec(
        select(Visitor).where(Visitor.physical_card_id == request.card_uid)
    ).first()
    
    if existing_card and existing_card.id != request.user_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Card UID '{request.card_uid}' is already linked to another user (ID: {existing_card.id})"
        )
    
    # C. Update the user's physical card ID
    user.physical_card_id = request.card_uid
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return LinkCardResponse(
        status="success",
        message=f"Physical card successfully linked to user {user.name or user.email}",
        user_id=user.id,
        card_uid=request.card_uid
    )

@app.post("/api/gate/scan", response_model=GateScanResponse)
def scan_at_gate(
    request: GateScanRequest,
    session: Session = Depends(get_session)
):
    """
    Authenticate a user at the gate using either their phone (HCE) or physical card.
    
    - Searches for a user where virtual_nfc_id OR physical_card_id matches the scanned_id
    - Returns ACCESS_GRANTED with welcome message if found
    - Returns ACCESS_DENIED if not found
    """
    # Query DB to find user with matching virtual OR physical NFC ID
    statement = select(Visitor).where(
        or_(
            Visitor.virtual_nfc_id == request.scanned_id,
            Visitor.physical_card_id == request.scanned_id
        )
    )
    
    user = session.exec(statement).first()
    
    if user:
        # Access Granted
        user_name = user.name or user.email.split('@')[0]  # Use name or email prefix
        return GateScanResponse(
            status="ACCESS_GRANTED",
            user_name=user_name,
            welcome_message=f"Welcome back, {user_name}!"
        )
    else:
        # Access Denied
        return GateScanResponse(
            status="ACCESS_DENIED"
        )