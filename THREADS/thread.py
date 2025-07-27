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
from dotenv import load_dotenv

# Set the standard output to handle UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Define your access token, Instagram account ID, and the video details
# Get All required Tokens and Ids,
load_dotenv()
APP_ID = os.getenv('APP_ID')
APP_SECRET = os.getenv('APP_SECRET')
API_VERSION = os.getenv('API_VERSION')
THREADS_USER_ID = os.getenv('THREADS_USER_ID')
THREADS_ACCESS_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')
BASE_URL = os.getenv('THREADS_BASE_URL')
CHATGPT_KEY = os.getenv('CHATGPT_KEY')

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
    endpoint = f"/{API_VERSION}/debug_token?input_token={THREADS_ACCESS_TOKEN}&access_token={THREADS_ACCESS_TOKEN}"
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
    conn.request("GET", f"/{API_VERSION}/oauth/access_token?{params}")
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

def create_video_media_container(conn, media_type , params):

    query = urllib.parse.urlencode(params)
    endpoint = f"/v1.0/{THREADS_USER_ID}/threads?{query}&access_token={THREADS_ACCESS_TOKEN}"
    
    conn.request("POST", endpoint)
    res = conn.getresponse()
    data = res.read()
    conn.close()

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
    conn.close()

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
    
if __name__ == "__main__":
    conn = initialize_connection()
    prompt_file = 'THREADS/prompt.txt'
    user_prompt = read_prompt(prompt_file)

    TEXT = call_openai(user_prompt, CHATGPT_KEY)
    print("Response:\n", TEXT)
    IMAGE_URL = "https://your-public-server.com/path/to/image.jpg"
    VIDEO_URL = "https://your-public-server.com/path/to/video.mp4"
    
    # Check and refresh access token before proceeding
    print("ACCESS TOKEN = ",THREADS_ACCESS_TOKEN)
    check_access_token(conn)    
    print("ACCESS TOKEN = ",THREADS_ACCESS_TOKEN)

    print("Creating media container...")
    # # media_type = ["TEXT","IMAGE","VIDEO"]
    media_type = ["TEXT"]
    media_type = random.choice(media_type)  # Randomly select media type
    print(f"Selected media type: {media_type}")
    if media_type == "TEXT":
        print("Creating text media container...")
        params = {
            "media_type": media_type,
            "text": TEXT
        }
        container_id = create_video_media_container(conn, media_type, params)
    elif media_type == "IMAGE":
        print("Creating image media container...")
        params = {
            "media_type": media_type,
            "image_url": IMAGE_URL,
            "text": TEXT
        }
        container_id = create_video_media_container(conn, media_type, params)
    elif media_type == "VIDEO":
        print("Creating video media container...")
        params = {
            "media_type": media_type,
            "video_url": VIDEO_URL,
            "text": TEXT
        }
        container_id = create_video_media_container(conn, media_type, params)

    if container_id:
        print(f"Media container created: {container_id}")
        print("Waiting 30 seconds for processing...")
        time.sleep(30)

        print("Publishing media container...")
        post_id = publish_media_container(conn, container_id)
        
        if post_id:
            print(f"✅ Post published successfully! Post ID: {post_id}")
        else:
            print("❌ Failed to publish the post.")
    else:
        print("❌ Failed to create media container.")
    
    conn.close()
