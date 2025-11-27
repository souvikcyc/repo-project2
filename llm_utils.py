import os
import json
import logging
import subprocess
import traceback
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")

client = AsyncOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

async def run_python_code(code: str) -> str:
    """
    Executes Python code in a separate process and returns stdout/stderr.
    """
    logger.info(f"Executing Python code:\n{code}")
    try:
        # Write code to a temporary file
        with open("temp_script.py", "w", encoding="utf-8") as f:
            f.write(code)
            
        # Execute it
        # We use the current venv python
        python_executable = "./venv/Scripts/python" if os.path.exists("./venv/Scripts/python") else "python"
        
        result = subprocess.run(
            [python_executable, "temp_script.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        if result.stderr:
            output += "\nError:\n" + result.stderr
            
        return output
    except Exception as e:
        return f"Execution failed: {e}\n{traceback.format_exc()}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Executes Python code to perform data analysis, file reading, or calculations. The code has access to pandas, numpy, sklearn, etc. Always print the final result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute."
                    }
                },
                "required": ["code"]
            }
        }
    }
]

async def analyze_task_and_generate_code(html_content: str, text_content: str) -> dict:
    """
    Analyzes the quiz page content and returns the answer and submission URL.
    """
    system_prompt = """
    You are an autonomous agent solving a data analysis quiz.
    Your goal is to:
    1. Identify the question and the submission URL from the page content.
    2. Solve the question. Use the `run_python` tool to process data, download files, or perform calculations.
    3. Return the final answer and submission URL in JSON format.
    
    When using `run_python`:
    - You can use `requests` to download files.
    - You can use `pandas` to analyze data.
    - PRINT the result you want to see.
    
    Format your FINAL response (when you have the answer) as a JSON object:
    {
        "answer": <answer>,
        "submission_url": <url>,
        "reasoning": <brief reasoning>
    }
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Page Text:\n{text_content[:5000]}\n\nPage HTML Source:\n{html_content[:5000]}"}
    ]
    
    # Agent loop
    for _ in range(5): # Max 5 turns
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",

            )
            
            msg = response.choices[0].message
            messages.append(msg)
            
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.function.name == "run_python":
                        args = json.loads(tool_call.function.arguments)
                        code = args["code"]
                        output = await run_python_code(code)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": output
                        })
            else:
                # No tool calls, assume it's the final answer
                content = msg.content
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # If it's not JSON, maybe it's just text. We can try to parse or ask again.
                    # For now, let's log and return None or try to extract JSON.
                    logger.warning(f"Failed to parse JSON from: {content}")
                    # Try to find JSON block
                    if "{" in content and "}" in content:
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        return json.loads(content[start:end])
                    return None
                    
        except Exception as e:
            logger.error(f"Error in agent loop: {e}")
            return None
            
    return None
