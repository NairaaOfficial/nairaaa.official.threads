import http.client
import urllib.parse
import json
import time
import sys
import io
import os
import openai
from openai import OpenAI
from datetime import datetime
import random

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
CHATGPT_KEY = os.environ['CHATGPT_KEY']
RENDER_BASE_VIDEO_URL = os.environ['RENDER_BASE_VIDEO_URL']

def initialize_connection():
    """Initialize the HTTP connection to Instagram Graph API."""
    return http.client.HTTPSConnection(BASE_URL)

def call_openai(
    prompt: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    model: str = "deepseek/deepseek-chat-v3-0324:free",
    extra_headers: dict = None,
    extra_body: dict = None
) -> str:
    """
    Uses OpenAI's SDK to get a response from OpenRouter API endpoint.

    Parameters:
        prompt (str): Prompt to send to the model.
        api_key (str): Your OpenRouter API key.
        base_url (str): API endpoint URL.
        model (str): Model name.
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
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            extra_headers=extra_headers or {},
            extra_body=extra_body or {}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"


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

def filter_generated_text(text):
    """
    Filters the generated text to remove any unwanted content, such as special characters like * or **.
    """
    # Remove all occurrences of * and ** from the text
    filtered_text = text.replace("*", "")
    filtered_text = filtered_text.replace("\"", "")
    return filtered_text

def create_video_media_container(conn, VIDEO_URL, TEXT):

    params = {
        "media_type": "VIDEO",
        "video_url": VIDEO_URL,
        "text": TEXT
    }

    query = urllib.parse.urlencode(params)
    endpoint = f"/v1.0/{THREADS_USER_ID}/threads?{query}&access_token={THREADS_ACCESS_TOKEN}"
    
    conn.request("POST", endpoint)
    res = conn.getresponse()
    data = res.read()

    if res.status != 200:
        print(f"Error creating media container: {res.status} {res.reason}")
        print(data.decode("utf-8"))
        return None

    result = json.loads(data.decode("utf-8"))
    return result.get("id")

def publish_media_container(conn, media_container_id):
    params = {
        "creation_id": media_container_id
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

def get_video_urls_for_day(counter):
    """
    Returns a list of valid video URLs for a given day.
    Stops when a video is not found or max_attempts is reached.
    """
    
    url = f"{RENDER_BASE_VIDEO_URL}/Video_{counter}.mp4"
    parsed_url = urllib.parse.urlparse(url)
    conn = http.client.HTTPSConnection(parsed_url.netloc)
    conn.request("HEAD", parsed_url.path)
    response = conn.getresponse()
    if response.status == 200:
        return url
    else:
        return None
    

def read_counter(counter_file):
    """Read the current counter value from the file, or initialize it."""
    if os.path.exists(counter_file):
        with open(counter_file, 'r') as file:
            return int(file.read())
    return 0
    
if __name__ == "__main__":
    conn = initialize_connection()

    # Define a file to store the counter
    counter_file = 'counter_video.txt'    
    counter = read_counter(counter_file)
    
    # Execute the code
    print(f"Counter : {counter}")
    prompt_file = 'THREADS/prompt_image_video.txt'
    user_prompt = read_prompt(prompt_file)

    # Check and refresh access token before proceeding
    print("ACCESS TOKEN = ",THREADS_ACCESS_TOKEN)
    check_access_token(conn)    
    print("ACCESS TOKEN = ",THREADS_ACCESS_TOKEN)

    TEXT = call_openai(user_prompt, CHATGPT_KEY)
    print("Generated TEXT:", TEXT)
    TEXT = filter_generated_text(TEXT)
    print("Filtered TEXT:", TEXT)
    VIDEO_URL = get_video_urls_for_day(counter)
    print("Video URL for the day:", VIDEO_URL)

    print("Creating video media container...")
    container_id = create_video_media_container(conn, VIDEO_URL, TEXT)

    if container_id:
        print(f"Media container created: {container_id}")

        print("Publishing media container...")
        post_id = publish_media_container(conn, container_id)
        
        if post_id:
            print(f"✅ Post published successfully! Post ID: {post_id}")
        else:
            print("❌ Failed to publish the post.")
    else:
        print("❌ Failed to create media container.")
    
    conn.close()
