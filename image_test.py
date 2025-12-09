import requests
import os

# CONFIGURATION
# ----------------
IMAGE_FILENAME = "image.png"  # <--- REPLACE THIS with your actual file name
API_URL = "http://127.0.0.1:8000/upload-photo/"

# DATA TO SEND
payload = {
    "visitor_id": 0,  # Ensure Visitor ID 1 exists in your DB
    "room_id": 1      # Ensure Room ID 1 exists in your DB
}

def upload_image():
    # Check if file exists first
    if not os.path.exists(IMAGE_FILENAME):
        print(f"Error: Could not find '{IMAGE_FILENAME}' in this folder.")
        print("Please move your image here or update the IMAGE_FILENAME variable.")
        return

    # Prepare the file
    # 'file' is the name of the parameter in your FastAPI endpoint
    files = {
        "file": (IMAGE_FILENAME, open(IMAGE_FILENAME, "rb"), "image/jpeg")
    }

    print(f"Uploading '{IMAGE_FILENAME}'...")
    
    try:
        response = requests.post(API_URL, data=payload, files=files)
        
        if response.status_code == 200:
            print("\n Success!")
            print(response.json())
        else:
            print(f"\n Failed (Status {response.status_code}):")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n Error: Could not connect to server.")
        print("Make sure it is running: uv run uvicorn main:app --reload")
    finally:
        files["file"][1].close()

if __name__ == "__main__":
    upload_image()