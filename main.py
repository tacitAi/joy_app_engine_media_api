from fastapi import FastAPI, HTTPException, UploadFile, File
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
import tempfile
import os
import subprocess
from google.cloud import storage
import uuid
from typing import List
from dotenv import load_dotenv

app = FastAPI()

BACKGROUND_SONG = "resources/good_morning_i_love_you_blank.mp3" 
BACKGROUND_VIDEO_NO_MUSIC = "resources/good_morning_i_love_you_no_music.mp4"

load_dotenv()  # Load environment variables from .env file

# Set up environment
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

# Get secrets
ELEVENLABS_API_KEY = access_secret(PROJECT_ID, 'ELEVENLABS_API_KEY')
MAIN_VOICE_ID = access_secret(PROJECT_ID, 'MAIN_VOICE_ID')
GOOD_MORNING_BUCKET_NAME = access_secret(PROJECT_ID, 'GOOD_MORNING_BUCKET_NAME')
MY_MOTHER_MY_QUEEN_BUCKET_NAME = access_secret(PROJECT_ID, 'MY_MOTHER_MY_QUEEN_BUCKET_NAME')

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket = storage_client.bucket(GOOD_MORNING_BUCKET_NAME)

def upload_to_gcs(file_path, destination_blob_name=None):
    """Uploads a file to the bucket."""
    if destination_blob_name is None:
        # Generate a unique filename if not provided
        destination_blob_name = f"videos/{uuid.uuid4()}.mp4"
    
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)

    # Make the blob publicly readable (optional - only if you want public URLs)
    blob.make_public()    
    return blob.public_url

def generate_audio_clips(sender: str, recipient: str):
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    
    hi_recipient = client.text_to_speech.convert(
        text=f"Hi {recipient}",
        voice_id=MAIN_VOICE_ID,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    sender_loves_recipient = client.text_to_speech.convert(
        text=f"{sender} loves you {recipient}",
        voice_id=MAIN_VOICE_ID,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    
    return hi_recipient, sender_loves_recipient

def mix_audio(background_path: str, overlay1: bytes, overlay2: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_overlay1, \
         tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_overlay2, \
         tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as output_file:
        
        # Write audio data to temporary files
        temp_overlay1.write(b"".join(overlay1))
        temp_overlay2.write(b"".join(overlay2))
        
        # Load audio segments
        background = AudioSegment.from_mp3(background_path)
        overlay1_audio = AudioSegment.from_mp3(temp_overlay1.name)
        overlay2_audio = AudioSegment.from_mp3(temp_overlay2.name)
        
        # Mix audio
        combined = background.overlay(overlay1_audio, position=4000)  # 4 seconds
        final = combined.overlay(overlay2_audio, position=36000)  # 36 seconds
        
        # Export result
        final.export(output_file.name, format="mp3")
        
        # Clean up temp files
        os.unlink(temp_overlay1.name)
        os.unlink(temp_overlay2.name)
        
        return output_file.name

def add_audio_to_video(video_path: str, audio_path: str) -> str:
    # Create temporary file for output
    output_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    output_video.close()
    
    try:
        # Combine video with audio using ffmpeg
        subprocess.run([
            "ffmpeg", "-i", video_path, "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", output_video.name, "-y"
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return output_video.name
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(output_video.name):
            os.unlink(output_video.name)
        raise e

@app.post("/goodmorning/video/en-US/{sender}/{recipient}")
async def create_greeting(
    sender: str,
    recipient: str
):
    temp_files = []  # Track temporary files for cleanup

    try:
        # Generate audio clips
        overlay1, overlay2 = generate_audio_clips(sender, recipient)
        
        # First mix the audio using the existing function
        mixed_audio_path = mix_audio(BACKGROUND_SONG, overlay1, overlay2)
        temp_files.append(mixed_audio_path)

        # Add the mixed audio to the video
        output_video_path = add_audio_to_video(BACKGROUND_VIDEO_NO_MUSIC, mixed_audio_path)
        temp_files.append(output_video_path)

        #destination_blob_name = f"videos/{sender.lower()}_{recipient.lower()}_{uuid.uuid4()}.mp4"
        # Generate unique destination blob name
        file_name = f"{sender[0].lower()}{recipient[0].lower()}{uuid.uuid4()}"
        destination_blob_name = f"videos/{file_name}.mp4"

        # Upload video to GCS
        video_url = upload_to_gcs(output_video_path, destination_blob_name)

        return {
            "status": "success",
            "message": "Good morning video created successfully",
            "url": video_url,
            "fileName": destination_blob_name,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary files
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.unlink(file_path)

# New endpoint to handle multiple image uploads
@app.post("/upload_images")
async def upload_multiple_images(images: List[UploadFile] = File(...)):
    """
    Endpoint to upload multiple images to Google Cloud Storage.
    """
    if len(images) > 10:
        raise HTTPException(status_code=400, detail="You can upload a maximum of 10 images.")
    
    try:
        return upload_images(images)  # Call the upload_images function from image_uploader.py
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Welcome to the JOY API - we are going to do great!!!"}
