import os
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from quiz_solver import solve_quiz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str
    # Allow extra fields
    class Config:
        extra = "allow"

@app.post("/run")
async def run_quiz(request: QuizRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to trigger the quiz solver.
    """
    # Verify secret (simple check against env var or hardcoded for now, as per instructions)
    # In a real scenario, we might want to validate against a known secret.
    # The instructions say: "Verify the secret matches what you provided in the Google Form."
    # Since we don't have the Google Form data, we'll assume the secret passed here is the one we expect
    # OR we can just log it. The prompt says "Verify the secret matches what you provided".
    # We'll assume the user sets a local env var for the expected secret.
    
    expected_secret = os.getenv("MY_SECRET")
    if expected_secret and request.secret != expected_secret:
        # However, the prompt implies we are the student, so we define the secret.
        # If the request comes FROM the evaluator, they send the secret WE gave them.
        # So we should check if it matches OUR secret.
        raise HTTPException(status_code=403, detail="Invalid secret")

    logger.info(f"Received quiz request for {request.email} at {request.url}")
    
    # Start the solver in the background
    background_tasks.add_task(solve_quiz, request.url, request.email, request.secret)
    
    return {"message": "Quiz processing started", "status": "processing"}

@app.get("/")
async def root():
    return {"message": "LLM Analysis Quiz Solver is running"}
