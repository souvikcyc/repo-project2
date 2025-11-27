import asyncio
import logging
from llm_utils import analyze_task_and_generate_code
from playwright.async_api import async_playwright
import httpx
import json

logger = logging.getLogger(__name__)

async def solve_quiz(url: str, email: str, secret: str):
    """
    Main logic to solve the quiz.
    """
    logger.info(f"Starting quiz solver for {url}")
    
    current_url = url
    
    # Safety limit to prevent infinite loops
    max_iterations = 10
    iteration = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create a new context with permissions if needed
        context = await browser.new_context()
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Iteration {iteration}: Visiting {current_url}")
            
            try:
                page = await context.new_page()
                await page.goto(current_url)
                
                # Wait for the content to load. The prompt says "JavaScript-rendered HTML page".
                # We might need to wait for specific elements.
                # Let's wait for the body to be present.
                await page.wait_for_selector("body")
                
                # Get the full HTML
                content = await page.content()
                
                # Also get text content for easier reading
                text_content = await page.evaluate("document.body.innerText")
                
                logger.info("Page content retrieved. Analyzing task...")
                
                # Use LLM to understand the task and generate code/answer
                # We pass the HTML/Text, and the user info
                result = await analyze_task_and_generate_code(content, text_content)
                
                logger.info(f"LLM Result: {result}")
                
                if not result:
                    logger.error("Failed to get a result from LLM.")
                    break
                
                answer = result.get("answer")
                submission_url = result.get("submission_url") # Extracted from page
                
                # If the LLM didn't find a submission URL, we might need to look harder or it's the end?
                # The prompt says "The quiz page always includes the submit URL to use."
                
                if not submission_url:
                    logger.error("No submission URL found.")
                    break
                    
                # Submit the answer
                payload = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": answer
                }
                
                logger.info(f"Submitting answer to {submission_url}: {payload}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(submission_url, json=payload, timeout=30.0)
                    
                logger.info(f"Submission response: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get("correct"):
                        logger.info("Answer correct!")
                        next_url = resp_json.get("url")
                        if next_url:
                            current_url = next_url
                            logger.info(f"Moving to next URL: {current_url}")
                        else:
                            logger.info("Quiz completed!")
                            break
                    else:
                        logger.warning(f"Answer incorrect. Reason: {resp_json.get('reason')}")
                        # Logic to retry? The prompt says "you are allowed to re-submit".
                        # For now, let's just break or maybe retry once?
                        # A robust agent would try to fix the error.
                        break
                else:
                    logger.error(f"Submission failed with status {response.status_code}")
                    break
                    
                await page.close()
                
            except Exception as e:
                logger.error(f"Error in solve_quiz loop: {e}")
                break
        
        await browser.close()
