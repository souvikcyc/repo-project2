# LLM Analysis Quiz Solver

This project implements an autonomous agent to solve data analysis quizzes using LLMs.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Set environment variables:
   ```bash
   export OPENAI_API_KEY="your_key"
   export OPENAI_BASE_URL="https://aipipe.org/openai/v1"
   export MY_SECRET="super-souvik-secret"
   ```

3. Run the server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Usage

Send a POST request to `/run` with the quiz details.
