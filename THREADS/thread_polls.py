import http.client
import urllib.parse
import json
import time
import sys
import io
import os
import random
from openai import OpenAI
from datetime import datetime

# Set the standard output to handle UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Define your access token, Instagram account ID, and the video details
# Get All required Tokens and Ids,
APP_ID = os.environ['APP_ID']
APP_SECRET = os.environ['APP_SECRET']
THREADS_API_VERSION = os.environ['THREADS_API_VERSION']
THREADS_USER_ID = os.environ['THREADS_USER_ID']
THREADS_ACCESS_TOKEN = os.environ['THREADS_ACCESS_TOKEN']
BASE_URL = os.environ['THREADS_BASE_URL']
THREADS_POLL_CAPTION_KEY = os.environ['THREADS_POLL_CAPTION_KEY']

# Default polls list
default_polls = [
    {
        "question": "Would you rather cuddle all night or kiss all night? 🛌💋",
        "options": {
            "option_a": "Cuddle 🛌",
            "option_b": "Kiss 💋",
        },
    },
    {
        "question": "Guess what I’m wearing right now… 🤔",
        "options": {
            "option_a": "Something comfy 🩳",
            "option_b": "Nothing at all 😏",
            "option_c": "Your favorite color 🎨",
        },
    },
    {
        "question": "Be honest: You like it naughty or nice? 😈😇",
        "options": {
            "option_a": "Naughty 😈",
            "option_b": "Nice 😇",
        },
    },
    {
        "question": "Who wants to help me pick tonight’s lingerie? 👀",
        "options": {
            "option_a": "Lace 🩲",
            "option_b": "Silk 🧵",
            "option_c": "Nothing 😏",
        },
    },
    {
        "question": "If I were your naughty secretary… what would you make me do? 🖋️📂",
        "options": {
            "option_a": "Take notes 📝",
            "option_b": "Stay late 🕒",
            "option_c": "Break all the rules 🚫",
        },
    },
    {
        "question": "Finish this: If we were on a date… 💑",
        "options": {
            "option_a": "We’d laugh all night 😂",
            "option_b": "We’d get into trouble 😜",
            "option_c": "We’d never want it to end ❤️",
        },
    },
    {
        "question": "Is it a red flag if a guy texts back too quickly? 🚩📱",
        "options": {
            "option_a": "Yes ✅",
            "option_b": "No ❌",
            "option_c": "Depends 🤔",
        },
    },
    {
        "question": "Big chest or big heart? ❤️💪",
        "options": {
            "option_a": "Big chest 💪",
            "option_b": "Big heart ❤️",
        },
    },
    {
        "question": "Lace or leather tonight? 🩲🖤",
        "options": {
            "option_a": "Lace 🩲",
            "option_b": "Leather 🖤",
        },
    },
    {
        "question": "Woke up feeling like trouble today. What should I do? 😈",
        "options": {
            "option_a": "Stay in bed 🛌",
            "option_b": "Go out and slay 💃",
        },
    },
    {
        "question": "Truth or dare in comments? 🤔🎲",
        "options": {
            "option_a": "Truth 🗣️",
            "option_b": "Dare 🎯",
        },
    },
    {
        "question": "What’s your favorite type of kiss? 😘",
        "options": {
            "option_a": "Soft and slow 💞",
            "option_b": "Passionate 🔥",
            "option_c": "Playful 😜",
        },
    },
    {
        "question": "What’s your ideal Friday night? 🎉🍷",
        "options": {
            "option_a": "Netflix & chill 📺🍿",
            "option_b": "Party all night 🎉",
            "option_c": "Dinner date 🍽️",
        },
    },
    {
        "question": "What’s your favorite way to flirt? 😉",
        "options": {
            "option_a": "Eye contact 👀",
            "option_b": "Playful teasing 😏",
            "option_c": "Compliments 💬",
        },
    }
]

def initialize_connection():
    """Initialize the HTTP connection to Instagram Graph API."""
    return http.client.HTTPSConnection(BASE_URL)

def get_gemini_caption(
    prompt: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    model: str = "google/gemini-2.0-flash-exp:free",
    extra_headers: dict = None,
    extra_body: dict = None
) -> str:
    """
    Uses OpenAI's SDK to get a text-only response from OpenRouter Gemini model.

    Parameters:
        prompt (str): Prompt to send to the model.
        api_key (str): Your OpenRouter API key.
        base_url (str): API endpoint URL.
        model (str): Model name (default Gemini).
        extra_headers (dict): Optional extra headers for OpenRouter.
        extra_body (dict): Optional extra body for OpenRouter.

    Returns:
        str: The model's reply.
    """
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=500,
            extra_headers=extra_headers or {},
            extra_body=extra_body or {}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def filter_generated_text(text):
    """
    Filters the generated text to remove any unwanted content, such as special characters like * or **.
    """
    # Remove all occurrences of * and ** from the text
    filtered_text = text.replace("*", "")
    filtered_text = filtered_text.replace("\"", "")
    return filtered_text

def check_access_token(conn):
    """
    Check if the current access token is valid.
    If not, refresh the token.
    """
    # global ACCESS_TOKEN  # Update global variable
    endpoint = f"/{THREADS_API_VERSION}/debug_token?input_token={THREADS_ACCESS_TOKEN}&access_token={THREADS_ACCESS_TOKEN}"
    conn.request("GET", endpoint)
    response = conn.getresponse()
    data = json.loads(response.read().decode('utf-8'))
    print("check_access_token_response = ", data)

    expires_at = data["data"]["expires_at"]
    print("expires_at = ",data["data"]["expires_at"])  
    token_expires_one = datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M:%S')
    print("Token expires on:", token_expires_one)
    current_time = datetime.now().timestamp()  # Current timestamp in UTC
    print("current_time = ",current_time)
    remaining_days = (expires_at - current_time) / 86400  # Convert seconds to days
    print("remaining_days = ",int(remaining_days))
    
    # Check the token's validity
    if int(remaining_days) == 2:
        print("Access token is invalid or expired. Refreshing...")
        refresh_access_token(conn)
    else:
        print("Access token is valid.")

def refresh_access_token(conn):
    """Refresh the access token using the App credentials."""
    global ACCESS_TOKEN  # Update the global variable
    params = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": ACCESS_TOKEN,
    })
    conn.request("GET", f"/{THREADS_API_VERSION}/oauth/access_token?{params}")
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))
    print("refresh_access_token_response = ", data)
    if 'access_token' in data:
        new_access_token = data['access_token']
        update_env_file("INSTAGRAM_ACCESS_TOKEN", new_access_token)
        print("Access token refreshed and updated in the .env file.")
        # Reload environment variables to update the token for the current session
        os.environ['INSTAGRAM_ACCESS_TOKEN'] = new_access_token
        ACCESS_TOKEN = new_access_token  # Update in-memory token
    else:
        print("Failed to refresh access token:", data.get('error', 'Unknown error'))

def update_env_file(key, value):
    """
    Updates the specified key-value pair in the .env file.
    If the key doesn't exist, it will be added.
    """
    env_file = "THREADS/.env"
    updated_lines = []
    key_found = False

    # Read the file and update the key if it exists
    if os.path.exists(env_file):
        with open(env_file, "r") as file:
            for line in file:
                if line.startswith(f"{key}="):
                    updated_lines.append(f"{key}={value}\n")
                    key_found = True
                else:
                    updated_lines.append(line)

    # If the key is not found, append it
    if not key_found:
        updated_lines.append(f"{key}={value}\n")

    # Write back the updated content to the file
    with open(env_file, "w") as file:
        file.writelines(updated_lines)
    print(f"Updated {key} in .env file.")



def create_poll_container(conn, TEXT, poll_options):
    """
    Create a poll container for a Threads post.

    Parameters:
        conn: HTTP connection object.
        TEXT (str): The text content of the post.
        poll_options (dict): A dictionary containing poll options (option_a, option_b, etc.).

    Returns:
        str: The poll container ID.
    """
    if not (2 <= len(poll_options) <= 4):
        raise ValueError("Poll must have between 2 and 4 options.")

    params = {
        "media_type": "TEXT",
        "text": TEXT,
        "poll_attachment": json.dumps(poll_options)
    }

    query = urllib.parse.urlencode(params)
    endpoint = f"/v1.0/{THREADS_USER_ID}/threads?{query}&access_token={THREADS_ACCESS_TOKEN}"

    try:
        conn.request("POST", endpoint)
        res = conn.getresponse()
        data = res.read()

        if res.status != 200:
            print(f"Error creating poll container: {res.status} {res.reason}")
            print(data.decode("utf-8"))
            return None

        result = json.loads(data.decode("utf-8"))
        return result.get("id")
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def publish_media_container(conn, poll_container_id):
    params = {
        "creation_id": poll_container_id
    }
    query = urllib.parse.urlencode(params)
    endpoint = f"/v1.0/{THREADS_USER_ID}/threads_publish?{query}&access_token={THREADS_ACCESS_TOKEN}"
    
    conn.request("POST", endpoint)
    res = conn.getresponse()
    data = res.read()

    if res.status != 200:
        print(f"Error publishing post: {res.status} {res.reason}")
        print(data.decode("utf-8"))
        return None

    result = json.loads(data.decode("utf-8"))
    return result.get("id")

def read_prompt(prompt_file):
    print (prompt_file)
    try:
        with open(prompt_file, "r", encoding="utf-8") as file:
            prompt = file.read()
        return prompt
    except FileNotFoundError:
        return "prompt file not found."
    except Exception as e:
        return f"An error occurred: {e}"
    
def parse_poll_output(text):
    """
    Parses the OpenAI output to extract the question and options.

    Parameters:
        text (str): The text generated by OpenAI in the polling format.

    Returns:
        tuple: A tuple containing the question (str) and a dictionary of options.
    """
    lines = text.splitlines()
    question = None
    options = {}

    for line in lines:
        if line.startswith("Question:"):
            question = line.replace("Question:", "").strip()
        elif line.startswith("Option A:"):
            options["option_a"] = line.replace("Option A:", "").strip()
        elif line.startswith("Option B:"):
            options["option_b"] = line.replace("Option B:", "").strip()
        elif line.startswith("Option C:"):
            options["option_c"] = line.replace("Option C:", "").strip()
        elif line.startswith("Option D:"):
            options["option_d"] = line.replace("Option D:", "").strip()

    if not question or len(options) < 2:
        raise ValueError("Invalid poll format. Ensure at least a question and two options are provided.")

    return question, options

def get_random_default_poll():
    """Returns a random poll from the default polls list."""
    poll = random.choice(default_polls)
    return poll["question"], poll["options"]

if __name__ == "__main__":
    conn = initialize_connection()
    prompt_file = 'THREADS/prompt_polls.txt'
    user_prompt = read_prompt(prompt_file)

    # Check and refresh access token before proceeding
    print("ACCESS TOKEN = ", THREADS_ACCESS_TOKEN)
    check_access_token(conn)
    print("ACCESS TOKEN = ", THREADS_ACCESS_TOKEN)

    TEXT = get_gemini_caption(user_prompt, THREADS_POLL_CAPTION_KEY)
    print("Generated TEXT:", TEXT)
    TEXT = filter_generated_text(TEXT)
    print("Filtered TEXT:", TEXT)

    post_id = None

    # Parse the OpenAI output
    try:
        question, poll_options = parse_poll_output(TEXT)
        print("Parsed Question:", question)
        print("Parsed Options:", poll_options)

        # Create poll container
        print("Creating poll container...")
        poll_container_id = create_poll_container(conn, question, poll_options)
        if poll_container_id:
            print(f"Poll container created: {poll_container_id}")
            print("Waiting 2 seconds for processing...")
            time.sleep(2)

            print("Publishing poll container...")
            post_id = publish_media_container(conn, poll_container_id)
            if post_id:
                print(f"✅ Poll post published successfully! Post ID: {post_id}")
            else:
                print("❌ Failed to publish the poll post.")
        else:
            print("❌ Failed to create poll container.")

    except ValueError as e:
        print(f"Error parsing poll output: {e}")
        print("Using a default poll instead.")
        question, poll_options = get_random_default_poll()
        print("Default Question:", question)
        print("Default Options:", poll_options)

        # Create poll container with default poll
        print("Creating poll container with default poll...")
        poll_container_id = create_poll_container(conn, question, poll_options)
        if poll_container_id:
            print(f"Poll container created: {poll_container_id}")
            print("Waiting 2 seconds for processing...")
            time.sleep(2)

            print("Publishing poll container...")
            post_id = publish_media_container(conn, poll_container_id)
            if post_id:
                print(f"✅ Poll post published successfully! Post ID: {post_id}")
            else:
                print("❌ Failed to publish the poll post.")
        else:
            print("❌ Failed to create poll container.")

    if post_id:
        conn.close()
