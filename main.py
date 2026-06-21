from extract import extract_toc_and_parse, extract_others_and_parse
import os
import json
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from config import REDIS_HOST, REDIS_PORT, REDIS_DB
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse              
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import uuid
from redis.asyncio import Redis
import asyncio
import redis
from google import genai


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Mentrax AI API", description="API for managing educational content and generating animations")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory for uploads (use /tmp on serverless hosts)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Mock function to get user_id from JWT - replace with your actual implementation
def get_user_id(request="ok") -> str:
    # This is a placeholder - you mentioned you have this code already
    return "user123"  # Replace with actual user_id extraction from JWT

# Models
class CourseContent(BaseModel):
    name: str
    books: Dict[str, Any] = {}
    others: Dict[str, Any] = {}

@app.post("/create_course")
async def create_course(request: Request, course_name: str = Form(...)):
    """
    Create a new course directory for the user.
    """
    user_id = get_user_id(request)
    logger.info(f"Create course request from user {user_id} for course {course_name}")
    
    # Create directory structure
    user_dir = UPLOAD_DIR / user_id
    course_dir = user_dir / course_name
    course_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Course {course_name} created for user {user_id}")
    return {"message": f"Course '{course_name}' created successfully", "course_name": course_name}



@app.post("/check_name")
async def check_name(request: Request):
    """
    Check if a chat name already exists.
    Currently always returns exists=False to allow any name to be used.
    """
    # Skip validation for now by always returning False
    return {"exists": True}

@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    print("websocket endpoint")
    # token = websocket.query_params.get("token")
    # if not token:
    #     await websocket.close(code=1008)  # Policy Violation
    #     return
    # try:
    #     payload = decode_token(token)
    #     user_id = payload.get("sub")
    #     if not user_id:
    #         await websocket.close(code=1008)
    #         return
    # except Exception as e:
    #     await websocket.close(code=1008)
    #     return
    user_id = get_user_id()
    # processed_messages = set()  # Track processed message IDs to prevent duplicates
    
    try:
        redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        channel = f"workflow_{user_id}"
        last_id="$"
    except Exception as e:
        print("Auth or Redis Error:", e)
        await websocket.close()

    try:
        while True:
            response = await redis.xread(
                streams={channel: last_id},
                block=5000,  # wait max 5s
                count=10     # read up to 10 messages
            )

            if response:
                messages=response[0][1]  # Get messages from the first stream
                for msg_id, data in messages:
                    # last_id = msg_id
                    
                    # # Skip if we've already processed this message
                    # if msg_id in processed_messages:
                    #     continue
                    
                    # # Add to processed messages
                    # processed_messages.add(msg_id)
                    
                    # Handle completed video case
                    if 'video_path' in data:
                        try:
                            video_path = data['video_path']
                            with open(video_path, 'rb') as video_file:
                                video_bytes = video_file.read()
                                # Send video as base64 encoded string
                                data['video_content'] = base64.b64encode(video_bytes).decode('utf-8')
                        except Exception as e:
                            logger.error(f"Error reading video file: {str(e)}")
                            data['error'] = f"Could not read video file: {str(e)}"
                    
                    # Handle text-audio pair case
                    elif 'audio_path' in data:
                        try:
                            audio_path = data['audio_path']
                            with open(audio_path, 'rb') as audio_file:
                                audio_bytes = audio_file.read()
                                # Send audio as base64 encoded string
                                data['audio_content'] = base64.b64encode(audio_bytes).decode('utf-8')
                        except Exception as e:
                            logger.error(f"Error reading audio file: {str(e)}")
                            data['error'] = f"Could not read audio file: {str(e)}"

                    await websocket.send_json(data)
                    print(f"✅ Sent data to WebSocket:")
                    print("topic:", data.get('topic', 'N/A'),"timestamp:", data.get('timestamp', 'N/A'))
                # last_id = messages[-1][0]

    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close(code=1011)
    finally:
        await redis.close()



@app.post("/upload_book")
async def upload_book(
    request: Request,
    file: UploadFile = File(...),
    index_start_page: int = Form(...),
    index_end_page: int = Form(...),
    # first_page_number: int = Form(...),
    course_name: str = Form(...)
):
    user_id = get_user_id(request)
    logger.info(f"Upload book request from user {user_id} for course {course_name}")
    
    # Create directory structure
    user_dir = UPLOAD_DIR / user_id
    course_dir = user_dir / course_name
    books_dir = course_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    # Generate a unique ID for the file
    unique_id = uuid.uuid4().hex[:8]
    # Make filename unique by adding the UUID
    file_name_parts = os.path.splitext(file.filename)
    unique_filename = f"{file_name_parts[0]}_{unique_id}{file_name_parts[1]}"
    # Use the unique filename instead of the original
    file_path = books_dir / unique_filename
    
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    # Process the PDF and extract TOC
    try:
        toc_data = extract_toc_and_parse(
            str(file_path),
            index_start_page,
            index_end_page
        )
        
        # Save the extracted data as JSON
        json_path = books_dir / f"{unique_filename.split('.')[0]}.json"
        with open(json_path, "w") as f:
            json.dump(toc_data, f, indent=4)
        
        logger.info(f"Successfully processed book {unique_filename} for user {user_id}")
        return {"message": "Book uploaded and processed successfully",  "json": toc_data}
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/upload_others")
async def upload_others(
    request: Request,
    file: UploadFile = File(...),
    course_name: str = Form(...)
):
    user_id = get_user_id(request)
    logger.info(f"Upload other material request from user {user_id} for course {course_name}")
    
    # Create directory structure
    user_dir = UPLOAD_DIR / user_id
    course_dir = user_dir / course_name
    others_dir = course_dir / "others"
    others_dir.mkdir(parents=True, exist_ok=True)
    unique_id = uuid.uuid4().hex[:8]
    # Make filename unique by adding the UUID
    file_name_parts = os.path.splitext(file.filename)
    unique_filename = f"{file_name_parts[0]}_{unique_id}{file_name_parts[1]}"
    # Save the uploaded file
    file_path = others_dir / unique_filename
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    # Process the PDF
    try:
        extracted_data = extract_others_and_parse(str(file_path))
        
        # Save the extracted data as JSON
        json_path = others_dir / f"{unique_filename.split('.')[0]}.json"
        with open(json_path, "w") as f:
            json.dump(extracted_data, f, indent=4)
        
        logger.info(f"Successfully processed other material {unique_filename} for user {user_id}")
        return {"message": "File uploaded and processed successfully", "file": unique_filename, "json": str(json_path)}
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/all_courses", response_model=List[CourseContent])
async def get_all_courses(request: Request):
    user_id = get_user_id(request)
    logger.info(f"Get all courses request from user {user_id}")
    
    user_dir = UPLOAD_DIR / user_id
    
    if not user_dir.exists():
        logger.info(f"No courses found for user {user_id}")
        return []
    
    courses = []
    
    for course_dir in user_dir.iterdir():
        if course_dir.is_dir():
            course_data = {"name": course_dir.name, "books": {}, "others": {}}
            
            # Get books and their JSON data
            books_dir = course_dir / "books"
            if books_dir.exists():
                for book_file in books_dir.glob("*.pdf"):
                    json_file = books_dir / f"{book_file.stem}.json"
                    if json_file.exists():
                        with open(json_file, "r") as f:
                            course_data["books"][book_file.name] = json.load(f)
            
            # Get other materials and their JSON data
            others_dir = course_dir / "others"
            if others_dir.exists():
                for other_file in others_dir.glob("*.pdf"):
                    json_file = others_dir / f"{other_file.stem}.json"
                    if json_file.exists():
                        with open(json_file, "r") as f:
                            course_data["others"][other_file.name] = json.load(f)
            
            courses.append(course_data)
            # print(f"Course found: {courses}")
    
    logger.info(f"Found {len(courses)} courses for user {user_id}")
    return courses

# Add a new endpoint for starting teaching
class TeachingRequest(BaseModel):
    course_name: str
    content_type: str  # books or others
    pdf_name: str  # with extension
    chapter_name: str
    mode: str = "detailed"
    previous_knowledge: str = "beginner"
    education_level: str = "high school"
    language: str = "english"
    pdf_page_for_book_page_1: int = 1
    voice :bool

@app.post("/start_teaching")
async def start_teaching(request: Request, teaching_req: TeachingRequest):
    user_id = get_user_id(request)
    logger.info(f"Start teaching request from user {user_id} for course {teaching_req.course_name}, type {teaching_req.content_type}, chapter {teaching_req.chapter_name}")
    
    if teaching_req.content_type not in ["books", "others"]:
        raise HTTPException(status_code=400, detail="Content type must be either 'books' or 'others'")
    voice_need=teaching_req.voice
    # Build paths
    user_dir = UPLOAD_DIR / user_id
    course_dir = user_dir / teaching_req.course_name
    content_dir = course_dir / teaching_req.content_type
    
    # Check if the PDF exists
    pdf_path = content_dir / teaching_req.pdf_name
    if not pdf_path.exists():
        logger.error(f"PDF file {teaching_req.pdf_name} not found in {teaching_req.content_type}")
        raise HTTPException(status_code=404, detail=f"PDF file {teaching_req.pdf_name} not found")
    
    # Look for the JSON file
    json_filename = f"{os.path.splitext(teaching_req.pdf_name)[0]}.json"
    json_path = content_dir / json_filename
    
    if not json_path.exists():
        logger.error(f"JSON file {json_filename} not found for {teaching_req.pdf_name}")
        raise HTTPException(status_code=404, detail=f"JSON data not found for {teaching_req.pdf_name}")
    
    # Create a directory for storing content if it doesn't exist
    content_base_dir = Path(f"CONTENT/{user_id}")
    pdf_content_dir = content_base_dir / teaching_req.pdf_name.replace('.', '_')
    pdf_content_dir.mkdir(parents=True, exist_ok=True)
    
    # Format the chapter name for directory
    formatted_chapter_name = teaching_req.chapter_name.replace(':', '_').replace(' ', '_')
    chapter_content_dir = pdf_content_dir / formatted_chapter_name
    
    # Check if content already exists
    if chapter_content_dir.exists():
        logger.info(f"Content for chapter {teaching_req.chapter_name} already exists")
        return {"message": "Content already exists", "content_path": str(chapter_content_dir)}
    
    # If not exists, process the content
    if teaching_req.content_type == "books":
        try:
            # Load JSON data
            with open(json_path, "r") as f:
                chapters_data = json.load(f)
            
            # Find the chapter data by chapter name
            chapter_data = None
            for item in chapters_data:
                if isinstance(item, list) and len(item) > 0 and item[0] == teaching_req.chapter_name:
                    chapter_data = item
                    break
            
            if chapter_data is None:
                logger.error(f"Chapter {teaching_req.chapter_name} not found in {teaching_req.pdf_name}")
                raise HTTPException(status_code=404, detail=f"Chapter {teaching_req.chapter_name} not found")
            
            # Process the chapter content
            from gen_topic import pcc

            print("before pcc.delay")
            pcc.delay(
                chapter_data, 
                teaching_req.pdf_page_for_book_page_1, 
                teaching_req.mode, 
                teaching_req.previous_knowledge, 
                teaching_req.education_level, 
                teaching_req.language,
                teaching_req.pdf_name,
                user_id,
                str(pdf_path),
                voice_need
            )
            logger.info(f"Successfully started processing content for chapter {teaching_req.chapter_name}")
            return {
                "message": f"Processing started for chapter {teaching_req.chapter_name}",
                "pdf": teaching_req.pdf_name,
                "chapter": teaching_req.chapter_name,
                "content_path": str(chapter_content_dir)
            }
            
            
        except Exception as e:
            logger.error(f"Error processing chapter content: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing chapter content: {str(e)}")
    else:
        # For 'others' type - to be implemented later
        return {
            "message": "Teaching for 'others' type is not yet implemented",
            "chapter": teaching_req.chapter_name,
            "pdf": teaching_req.pdf_name
        }


# Add a new endpoint for starting teaching
class FetchExisting(BaseModel):
    course_name: str
    content_type: str  # books or others
    pdf_name: str  # with extension
    chapter_name: str


async def process_redis_queue(user_id: str, paths_list: list, content_items: list):
    """
    Background task to send content items to Redis
    """
    logger.info(f"Starting background processing of {len(paths_list)} items for user {user_id}")
    for element in paths_list:
        try:
            if isinstance(element, dict):  # Ensure it's a dictionary
                print(f"Sending element to Redis: {element}")
                await asyncio.sleep(0.1)
                redis_client.xadd(f"workflow_{user_id}", element, maxlen=1000, approximate=True)
                content_items.append(element.get("topic", "unknown"))
                # Small delay to prevent overwhelming Redis
                
        except Exception as e:
            logger.error(f"Error sending element to Redis: {str(e)}")
    logger.info(f"Completed sending {len(content_items)} items to Redis for user {user_id}")


@app.post("/fetch_existing_content")
async def fetch_existing_content(request: Request, fetch_req: FetchExisting, background_tasks: BackgroundTasks):
    user_id = get_user_id(request)
    logger.info(f"Fetch existing content request from user {user_id} for course {fetch_req.course_name}, type {fetch_req.content_type}, chapter {fetch_req.chapter_name}")
    
    # Build paths
    content_base_dir = Path(f"CONTENT/{user_id}")
    pdf_content_dir = content_base_dir / fetch_req.pdf_name.replace('.', '_')
    
    # Format the chapter name for directory
    formatted_chapter_name = fetch_req.chapter_name.replace(':', '_').replace(' ', '_')
    chapter_content_dir = pdf_content_dir / formatted_chapter_name
    
    # Check if content directory exists
    if not chapter_content_dir.exists():
        logger.error(f"Content directory for chapter {fetch_req.chapter_name} not found")
        raise HTTPException(status_code=404, detail=f"No existing content found for {fetch_req.chapter_name}")
    
    # Track content for response
    content_items = []
    
    # Go through each subfolder in the chapter content directory
    for subfolder in chapter_content_dir.iterdir():
        if subfolder.is_dir():
            all_paths_file = subfolder / "all_paths.json"
            
            if all_paths_file.exists():
                try:
                    # Load the content paths
                    with open(all_paths_file, "r") as f:
                        paths_list = json.load(f)
                    
                    # Send each path item to Redis
                    # for element in paths_list:
                    #     print(f"Sending element to Redis: {element}")
                    #     redis_client.xadd(f"workflow_{user_id}", element, maxlen=1000, approximate=True)
                    #     content_items.append(element.get("topic", "unknown"))
                    
                    # logger.info(f"Successfully sent {len(paths_list)} items to Redis for user {user_id}")
                    background_tasks.add_task(process_redis_queue, user_id, paths_list, content_items)
                
                except Exception as e:
                    logger.error(f"Error processing all_paths.json in {subfolder}: {str(e)}")
                    continue
    
    if not content_items:
        return {"message": "No content items found to process"}
    
    return {
        "message": f"Successfully fetched {len(content_items)} content items",
        "content_items": content_items
    }






@app.post("/doubt")
async def doubt_handler(request: Request, doubt: dict):
    """
    Handle doubt requests from students about specific content.
    """
    user_id = get_user_id(request)
    logger.info(f"Doubt request from user {user_id} regarding {doubt.get('book')} - {doubt.get('chapter')}")
    
    question = doubt.get('question')
    context = doubt.get('context')
    chapter = doubt.get('chapter', 'Unknown Chapter')
    book = doubt.get('book', 'Unknown Book')
    
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    # Format book and chapter names for directory paths
    formatted_book = book.replace('.', '_')
    formatted_chapter = chapter.replace(':', '_').replace(' ', '_')
    
    # Build path to doubts.json
    content_base_dir = Path(f"CONTENT/{user_id}")
    chapter_dir = content_base_dir / formatted_book / formatted_chapter
    chapter_dir.mkdir(parents=True, exist_ok=True)
    doubts_file = chapter_dir / "doubts.json"
    
    # Initialize chat history
    chat_history = []
    
    # Check if doubts.json exists and load it
    if doubts_file.exists():
        try:
            with open(doubts_file, "r") as f:
                chat_history = json.load(f)

            # Take last 6 elements or all if less than 6
            chat_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        except Exception as e:
            logger.error(f"Error reading doubts file: {str(e)}")
            chat_history = []
    
    
    
    # Generate response using LLM
    try:
        # This is a placeholder for your actual LLM implementation
        # You would need to replace this with your actual LLM call
        
        # Create prompt with history and context
        history_text = ""
        for msg in chat_history:
            role = "User" if msg["type"] == "user" else "Assistant"
            history_text += f"{role}: {msg['msg']}\n"
        
        
        template=f"""
        You are an educational AI assistant helping a student with their doubts.
        
        Chat history:
        {history_text}
        
        Context about the current topic:
        {context}
        
        Answer the following question based on the context and chat history:
        {question}
        
        Provide a clear and concise explanation. No preambles or postambles.
        Use simple language suitable for students.
        """
        client = genai.Client(api_key=os.getenv("GEMINI"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[template],
        ).text
    
        
        
        # Add user question to history
        user_message = {"type": "user", "msg": question}
        chat_history.append(user_message)
        # Add AI response to history
        ai_message = {"type": "ai", "msg": response}
        chat_history.append(ai_message)
        
        # Save updated chat history
        with open(doubts_file, "w") as f:
            json.dump(chat_history, f, indent=2)
        
        return {"answer": response, "success": True}
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        # Save just the user question if LLM fails
        with open(doubts_file, "w") as f:
            json.dump(chat_history, f, indent=2)
        
        return {"text": "I'm sorry, I couldn't generate a response at this time.", "error": str(e), "success": False}




@app.get("/get_doubts")
async def get_doubts(request: Request, book: str, chapter: str):
    """
    Retrieve saved doubts for a specific book chapter.
    """
    user_id = get_user_id(request)
    logger.info(f"Retrieving doubts for user {user_id}, book: {book}, chapter: {chapter}")
    
    # Format book and chapter names for directory paths
    formatted_book = book.replace('.', '_')
    formatted_chapter = chapter.replace(':', '_').replace(' ', '_')
    
    # Build path to doubts.json
    content_base_dir = Path(f"CONTENT/{user_id}")
    chapter_dir = content_base_dir / formatted_book / formatted_chapter
    doubts_file = chapter_dir / "doubts.json"
    
    # Check if doubts file exists
    if not doubts_file.exists():
        logger.info(f"No doubts found for book: {book}, chapter: {chapter}")
        return {"doubts": [], "message": "No doubts found for this chapter"}
    
    # Read and return the doubts
    try:
        with open(doubts_file, "r") as f:
            doubts = json.load(f)
        
        logger.info(f"Successfully retrieved {len(doubts)} doubts for user {user_id}")
        return {"doubts": doubts, "success": True}
    except Exception as e:
        logger.error(f"Error reading doubts file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving doubts: {str(e)}")










"""
before opening AI teaching platform, keep a page, where user can select either of AI teaching platform and mock interview .

Now,  I want you to create a professional mock interview interface. In this interface, user will have following options to add:-
- resume (optional)
- job description (optional)
compulsory fields:-
- mock interview type (HR round, DSA round, SYSTEM DESIGN round,  Project discussion, General interview, behavioural round, aptitude round, OA round)
- job role (Product manager, data scientist, ML engineer, AI engineer, SDE, Full stack Developer,  solution architect, devops engineer,  sales manager, Marketing executive...etc)
- duration (15 mins, 30 mins, 45 mins, 1 hr)

Now, after selecting, user can click on save preferences button, which will send request to /create_mock , and it returns a session_id , now  redirect user to access interview page,  ask for user's camera , mic and speaker access. user can allow them . and show all 3 are working. after that,  when use clicks on start interview, send a request to /start_mock with session_id , this route returns the first welcoming message (voice+text pair) then redirect to main page. this page will have a professional user interface with AI blend.  User should feel that he is in an interview with a professional AI. play the voice and display the text, during playing, turn the user's mic off.  also show some animation like AI is speaking.
when the voice completely gets played, Show somewhere LISTENING... , and turn the mic on, start recording user's voice, use webkit to convert voice to text in real time and show the text as user speaks.
when there is a silence of 5 seconds, mark that user ended speaking. now send the request to /mock with session_id and user's text, now it also responses with a text+voice pair,  and flag =1 . if flag is 1 play it and display the text and continue this until flag is 0 .  if flag is 0, then play and display the text ,  and display the leave button at bottom

when user clicks on leave, send request to /fetch_results with the session_id, it is basically json with ratings and conclusion {"topic A":6,"topic B":9,"conclusion":"Final conclusio according to interview"}

display this interactively - ratings using horizontal bar, conclusion

"""




import datetime
import random
from gtts import gTTS
import tempfile
import PyPDF2
@app.post("/create_mock")
async def create_mock(
    request: Request,
    resume: Optional[UploadFile] = File(None),
    job_description: str = Form(...),
    interview_type: str = Form(...),
    job_role: str = Form(...),
    duration: str = Form(...),
):
    """
    Create a mock interview session based on user preferences.
    
    Parameters:
    - resume: Optional PDF file of the user's resume
    - job_description: Job description text
    - interview_type: Type of interview (HR, DSA, System Design, etc.)
    - job_role: Job role being interviewed for
    - duration: Duration of the interview
    
    Returns:
    - session_id: Unique identifier for this interview session
    """
    user_id = get_user_id(request)
    logger.info(f"Creating mock interview for user {user_id}, type: {interview_type}, role: {job_role}")
    
    # Create a unique session ID
    session_id = f"interview_{uuid.uuid4().hex}"
    
    # Create directory for this interview session
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Save resume if provided
    resume_path = None
    if resume:
        resume_path = session_dir / "resume.pdf"
        try:
            with open(resume_path, "wb") as f:
                shutil.copyfileobj(resume.file, f)
        except Exception as e:
            logger.error(f"Error saving resume: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Could not save resume: {str(e)}")
    
    # Save session metadata
    session_data = {
        "user_id": user_id,
        "created_at": str(datetime.datetime.now()),
        "interview_type": interview_type,
        "job_role": job_role,
        "duration": duration,
        "job_description": job_description,
        "resume_path": str(resume_path) if resume_path else None,
        "status": "created"
    }
    
    metadata_path = session_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(session_data, f, indent=4)
    
    # Store in Redis for quick access
    # redis_client.hset(f"interview:{session_id}", mapping=session_data)
    # redis_client.expire(f"interview:{session_id}", 86400)  # Expire after 24 hours
    
    logger.info(f"Mock interview session created: {session_id}")
    return {"session_id": session_id, "message": "Mock interview session created successfully"}

@app.post("/start_mock")
async def start_mock(request: Request, came:dict):
    """
    Start a mock interview session and return the initial welcome message.
    """
    session_id = came.get("session_id")
    user_id = get_user_id(request)
    logger.info(f"Starting mock interview session {session_id} for user {user_id}")
    
    # Retrieve session data
    # session_data = redis_client.hgetall(f"interview:{session_id}")
    
    # Fallback to file if not in Redis
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    metadata_path = session_dir / "metadata.json"
    
    if not metadata_path.exists():
        logger.error(f"Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    with open(metadata_path, "r") as f:
        session_data = json.load(f)
    
    # Update session status
    session_data["status"] = "active"
    session_data["started_at"] = str(datetime.datetime.now())
    
    # Save updated status
    # redis_client.hset(f"interview:{session_id}", "status", "active")
    # redis_client.hset(f"interview:{session_id}", "started_at", str(datetime.datetime.now()))
    
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    metadata_path = session_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(session_data, f, indent=4)
    
    # Generate welcome message based on interview type and role
    interview_type = session_data.get(b"interview_type", "").decode() if isinstance(session_data.get("interview_type", ""), bytes) else session_data.get("interview_type", "")
    job_role = session_data.get(b"job_role", "").decode() if isinstance(session_data.get("job_role", ""), bytes) else session_data.get("job_role", "")
    
    welcome_message = f"Hello and welcome to your {interview_type} interview for the {job_role} position. I'll be your interviewer today. Let's get started. Could you please introduce yourself briefly?"
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    conversation_path = session_dir / "conversation.json"
    conversation=[]
    conversation.append({
        "role": "ai",
        "text": welcome_message,
        "timestamp": str(datetime.datetime.now()),
    })
    # Save updated conversation
    with open(conversation_path, "w") as f:
        json.dump(conversation, f, indent=4)

    # Generate audio for welcome message using Google Text-to-Speech
    try:
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            tts = gTTS(text=welcome_message, lang='en', slow=False)
            tts.save(temp_audio.name)
            
            # Read the audio file and convert to base64
            with open(temp_audio.name, 'rb') as audio_file:
                base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')
            
        # Clean up the temporary file
        os.unlink(temp_audio.name)
        
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        base64_audio = ""  # Empty string if audio generation fails
    logger.info(f"Mock interview {session_id} started")
    return {
        "text": welcome_message,
        "voice": base64_audio,  # Will be added when TTS is implemented
    }

@app.post("/mock")
async def mock_interview_qa(
    request: Request,
    came: dict,
):
    """
    Process user's response and generate the next interview question.
    """
    user_id = get_user_id(request)
    session_id = came.get("session_id")
    user_text = came.get("user_text", "")
    logger.info(f"Processing response for session {session_id}, user {user_id}")
    
    # Retrieve session data
    # session_data = redis_client.hgetall(f"interview:{session_id}")
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    metadata_path = session_dir / "metadata.json"
    
    if not metadata_path.exists():
        logger.error(f"Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    with open(metadata_path, "r") as f:
        session_data = json.load(f)
    if not session_data:
        logger.error(f"Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    # Save user's response
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    conversation_path = session_dir / "conversation.json"
    
    conversation = []
    if conversation_path.exists():
        with open(conversation_path, "r") as f:
            conversation = json.load(f)
    
    job_role = session_data.get("job_role", "Unknown Role")
    interview_type = session_data.get("interview_type", "General Interview")
    job_description = session_data.get("job_description", "No job description provided")
    resume = session_data.get("resume_path", None)
    # Extract text from resume if available
    resume_text = ""
    if resume and os.path.exists(resume):
        try:
            
            with open(resume, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    resume_text += page.extract_text() + "\n"
            
            logger.info(f"Successfully extracted text from resume for session {session_id}")
        except Exception as e:
            logger.error(f"Error extracting text from resume: {str(e)}")
            resume_text = "Could not extract text from resume."
    
    INTERVIEWER_PROMPT = f"""
    You are an AI interviewer conducting a mock interview. Your task is to ask relevant questions based on the user's previous responses and the job role they are applying for.
    Use the following guidelines:
    - Ask open-ended questions that allow the user to elaborate on their skills and experiences.
    - Tailor your questions based on the user's job role , interview type, job description, and resume (if provided).
    - Avoid asking questions that have already been answered in the conversation.
    - Keep the conversation professional and focused on the interview topic.
    - If the user provides a short or vague answer, STRICTLY ask follow-up questions to encourage them to elaborate.
    - If the user seems to be struggling, provide hints or examples to guide them.
    - If the user has provided a resume, use it to ask questions about their previous experiences and skills, relating to the job requirements of the position they are applying for.
    - Don't keep the question too long, keep it concise and to the point.
    - Keep the order of the questions logical and relevant to the job role and interview type.
    - After each user response, analyze their answer, and generate the next question based on their previous responses.
    - Always end the interview with a positive note, thanking the user for their time and participation.
    DATA:
    - Job role: {job_role}
    - Interview type: {interview_type}
    - Job description: {job_description}
    ##################################

    - Resume: {resume_text}

    ##################################

    - User's previous responses: {conversation}

    ##################################

    Return the next question to ask the user in a professional manner, as if you are a real interviewer.
    No preambles or postambles, just return the question.
    """
    try:
        # sample_file = client.files.upload(file=resume, config={"display_name": resume})
        
        # Generate content using a regular prompt instead of system prompt
        client = genai.Client(api_key=os.getenv("GEMINI"))
        ai_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[INTERVIEWER_PROMPT],
        ).text
    except Exception as e:
        print("gemini upload file or generating error:", e)


    conversation.append({
        "role": "user",
        "text": user_text,
        "timestamp": str(datetime.datetime.now())
    })


    # Check if interview duration has been exceeded
    current_time = datetime.datetime.now()
    started_at_str = session_data.get("started_at")
    duration_str = session_data.get("duration")
    
    # Convert started_at to datetime object
    try:
        started_at = datetime.datetime.fromisoformat(started_at_str)
    except (ValueError, TypeError):
        # If there's an error parsing the date, use a fallback
        started_at = current_time - datetime.timedelta(minutes=5)
    
    # Convert duration to minutes
    try:
        if 'min' in duration_str:
            duration_mins = int(duration_str.split(' ')[0])
        elif 'hr' in duration_str:
            duration_mins = int(float(duration_str.split(' ')[0]) * 60)
        else:
            duration_mins = 15  # Default to 15 mins if parsing fails
    except (ValueError, TypeError):
        duration_mins = 15  # Default to 15 mins
    
    # Calculate end time
    end_time = started_at + datetime.timedelta(minutes=duration_mins)
    
    # Determine if interview should end based on time or conversation length
    print("current time:", current_time)
    print("end time:", end_time)
    flag = 0 if (current_time >= end_time) else 1
    
    # Add AI response to conversation
    conversation.append({
        "role": "ai",
        "text": ai_response,
        "timestamp": str(datetime.datetime.now()),
    })
    
    # Save updated conversation
    with open(conversation_path, "w") as f:
        json.dump(conversation, f, indent=4)
    
    # Generate audio for welcome message using Google Text-to-Speech
    try:
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            tts = gTTS(text=ai_response, lang='en', slow=False)
            tts.save(temp_audio.name)
            
            # Read the audio file and convert to base64
            with open(temp_audio.name, 'rb') as audio_file:
                base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')
            
        # Clean up the temporary file
        os.unlink(temp_audio.name)
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        base64_audio = ""  # Empty string if audio generation fails
    logger.info(f"Generated response for session {session_id}, flag: {flag}")
    return {
        "text": ai_response,
        "flag": flag,
        "voice": base64_audio,  # Will be added when TTS is implemented
    }

@app.post("/fetch_results")
async def fetch_interview_results(request: Request, session_id: str = Form(...)):
    """
    Generate and return feedback and ratings for the completed interview.
    """
    user_id = get_user_id(request)
    logger.info(f"Fetching results for session {session_id}, user {user_id}")
    
    # Retrieve conversation
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    conversation_path = session_dir / "conversation.json"
    
    if not conversation_path.exists():
        logger.error(f"Conversation for session {session_id} not found")
        raise HTTPException(status_code=404, detail="Interview conversation not found")
    
    with open(conversation_path, "r") as f:
        conversation = json.load(f)
    
    # TODO: Use LLM to analyze conversation and generate feedback
    # For demonstration, generate simple feedback
    
    # Get session data for context
    session_dir = UPLOAD_DIR / user_id / "interviews" / session_id
    metadata_path = session_dir / "metadata.json"
    interview_type = ""
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            interview_type = json.load(f).get("interview_type", "")
    
    # Generate mock feedback
    if interview_type == "HR round":
        ratings = {
            "Communication Skills": random.randint(6, 9),
            "Confidence": random.randint(5, 9),
            "Relevant Experience": random.randint(6, 9),
            "Cultural Fit": random.randint(5, 9),
            "Overall Impression": random.randint(6, 9)
        }
        conclusion = "You demonstrated good communication skills and relevant experience. Work on providing more concise answers and highlighting specific achievements."
    elif interview_type == "DSA round":
        ratings = {
            "Problem Solving": random.randint(5, 9),
            "Code Quality": random.randint(5, 8),
            "Time Complexity Analysis": random.randint(4, 8),
            "Space Complexity Analysis": random.randint(4, 8),
            "Technical Knowledge": random.randint(6, 9)
        }
        conclusion = "You showed good problem-solving skills but could improve on optimizing solutions and discussing time/space complexity more thoroughly."
    else:
        ratings = {
            "Technical Knowledge": random.randint(6, 9),
            "Communication Skills": random.randint(5, 9),
            "Problem Solving": random.randint(6, 8),
            "Relevant Experience": random.randint(5, 9),
            "Overall Fit": random.randint(6, 9)
        }
        conclusion = "You performed well overall. Your technical knowledge is strong, and you communicated clearly. Consider providing more specific examples from your past experience."
    
    # Save results
    results = {
        "ratings": ratings,
        "conclusion": conclusion,
        "timestamp": str(datetime.datetime.now())
    }
    
    results_path = session_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=4)
    
    logger.info(f"Generated results for session {session_id}")
    return results



# Run the FastAPI app with uvicorn if this file is executed directly
if __name__ == "__main__":
    import uvicorn





    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

