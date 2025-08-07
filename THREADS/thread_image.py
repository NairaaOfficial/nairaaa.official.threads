import http.client
import urllib.parse
import json
import time
import sys
import io
import os
from openai import OpenAI
from datetime import datetime
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
RENDER_BASE_IMAGE_URL = os.getenv('RENDER_BASE_IMAGE_URL')

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

def create_single_image_container(conn, IMAGE_URL, TEXT):

    params = {
        "media_type": "IMAGE",
        "image_url": IMAGE_URL,
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

def publish_single_media_container(conn, media_container_id):
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

def create_item_container(conn, media_url, is_carousel_item=True):
    """
    Create an item container for an image in a carousel.

    Parameters:
        conn: HTTP connection object.
        media_url (str): URL of the image.
        is_carousel_item (bool): Indicates if the item is part of a carousel.

    Returns:
        str: The item container ID.
    """

    params = {
        "media_type": "IMAGE",
        "is_carousel_item": str(is_carousel_item).lower(),
        "image_url": media_url
    }

    query = urllib.parse.urlencode(params)
    endpoint = f"/v1.0/{THREADS_USER_ID}/threads?{query}&access_token={THREADS_ACCESS_TOKEN}"

    conn.request("POST", endpoint)
    res = conn.getresponse()
    data = res.read()

    if res.status != 200:
        print(f"Error creating item container: {res.status} {res.reason}")
        print(data.decode("utf-8"))
        return None

    result = json.loads(data.decode("utf-8"))
    return result.get("id")

def create_carousel_container(conn, children, TEXT):
    """
    Create a carousel container from item containers.

    Parameters:
        conn: HTTP connection object.
        children (list): List of item container IDs.
        text (str): Optional text for the carousel post.

    Returns:
        str: The carousel container ID.
    """
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
    }
    if TEXT:
        params["text"] = TEXT

    query = urllib.parse.urlencode(params)
    endpoint = f"/v1.0/{THREADS_USER_ID}/threads?{query}&access_token={THREADS_ACCESS_TOKEN}"

    conn.request("POST", endpoint)
    res = conn.getresponse()
    data = res.read()

    if res.status != 200:
        print(f"Error creating carousel container: {res.status} {res.reason}")
        print(data.decode("utf-8"))
        return None

    result = json.loads(data.decode("utf-8"))
    return result.get("id")

def publish_carousel_container(conn, carousel_container_id):
    """
    Publish a carousel container.

    Parameters:
        conn: HTTP connection object.
        carousel_container_id (str): The carousel container ID.

    Returns:
        str: The published post ID.
    """
    params = {
        "creation_id": carousel_container_id
    }
    query = urllib.parse.urlencode(params)
    endpoint = f"/v1.0/{THREADS_USER_ID}/threads_publish?{query}&access_token={THREADS_ACCESS_TOKEN}"

    conn.request("POST", endpoint)
    res = conn.getresponse()
    data = res.read()

    if res.status != 200:
        print(f"Error publishing carousel: {res.status} {res.reason}")
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

def get_image_urls_for_day(counter, max_attempts=20):
    """
    Returns a list of valid image URLs for a given day.
    Stops when an image is not found or max_attempts is reached.
    """
    urls = []
    for idx in range(1, max_attempts + 1):
        url = f"{RENDER_BASE_IMAGE_URL}/{counter}_{idx}.png"
        parsed_url = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed_url.netloc)
        conn.request("HEAD", parsed_url.path)
        response = conn.getresponse()
        if response.status == 200:
            urls.append(url)
        else:
            break
    return urls

def read_counter(counter_file):
    """Read the current counter value from the file, or initialize it."""
    if os.path.exists(counter_file):
        with open(counter_file, 'r') as file:
            return int(file.read())
    return 0
    
if __name__ == "__main__":
    conn = initialize_connection()

    # Define a file to store the counter
    counter_file = 'counter.txt'    
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
    image_urls = get_image_urls_for_day(counter)
    print("Image URLs for the day:", image_urls)

    if len(image_urls) == 1:
        IMAGE_URL = image_urls[0]
        print("Creating image media container...")
        container_id = create_single_image_container(conn, IMAGE_URL, TEXT)

        if container_id:
            print(f"Image container created: {container_id}")
            print("Waiting 30 seconds for processing...")
            time.sleep(30)

            print("Publishing media container...")
            post_id = publish_single_media_container(conn, container_id)

            if post_id:
                print(f"✅ Post published successfully! Post ID: {post_id}")
            else:
                print("❌ Failed to publish the post.")
        else:
            print("❌ Failed to create media container.")
    else:
        print("Creating carousel item containers...")
        item_container_ids = []
        for url in image_urls:
            item_id = create_item_container(conn, url)
            if item_id:
                item_container_ids.append(item_id)
            else:
                print(f"❌ Failed to create item container for {url}")

        if item_container_ids:
            print("Waiting 30 seconds for processing carousel items...")
            time.sleep(30)
            print("Creating carousel container...")
            carousel_id = create_carousel_container(conn, item_container_ids, TEXT)
            if carousel_id:
                print(f"Carousel container created: {carousel_id}")
                print("Waiting 30 seconds for processing carousel...")
                time.sleep(30)
                print("Publishing carousel container...")
                post_id = publish_carousel_container(conn, carousel_id)
                if post_id:
                    print(f"✅ Carousel post published successfully! Post ID: {post_id}")
                else:
                    print("❌ Failed to publish the carousel post.")
            else:
                print("❌ Failed to create carousel container.")
        else:
            print("❌ No item containers created for carousel.")

    conn.close()
