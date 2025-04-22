from manage_secrets import access_secret
from audio_service import generate_good_moring_clips, generate_my_mother_my_queen_clips
from fastapi import FastAPI, HTTPException, Request
from pydub import AudioSegment
import tempfile
import os
import subprocess
from google.cloud import storage
import uuid
from dotenv import load_dotenv
import requests

app = FastAPI()

BACKGROUND_SONG = "resources/good_morning_i_love_you_blank.mp3" 
BACKGROUND_VIDEO_NO_MUSIC = "resources/good_morning_i_love_you_no_music.mp4"

LIGHTX_API_URL = "https://api.lightxeditor.com/external/api/v1/portrait"
LIGHTX_API_KEY = "99d0f16ad4e045d4a7eef3fb76daa2fa_945863be3a2641b9916b4e26db11641c_andoraitools"  # Replace with your actual API key

load_dotenv()  # Load environment variables from .env file

# Set up environment
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

# Get secrets
GOOD_MORNING_BUCKET_NAME = access_secret(PROJECT_ID, 'GOOD_MORNING_BUCKET_NAME')
MY_MOTHER_MY_QUEEN_BUCKET_NAME = access_secret(PROJECT_ID, 'MY_MOTHER_MY_QUEEN_BUCKET_NAME')

# Initialize Google Cloud Storage client
storage_client = storage.Client()

def upload_to_gcs(bucket, file_path, destination_blob_name=None):
    """Uploads a file to the specified bucket."""
    if destination_blob_name is None:
        # Generate a unique filename if not provided
        destination_blob_name = f"videos/{uuid.uuid4()}.mp4"
    
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)

    # Make the blob publicly readable (optional - only if you want public URLs)
    blob.make_public()    
    return blob.public_url

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
    bucket = storage_client.bucket(GOOD_MORNING_BUCKET_NAME)

    try:
        # Generate audio clips
        overlay1, overlay2 = generate_good_moring_clips(sender, recipient)
        
        # First mix the audio using the existing function
        mixed_audio_path = mix_audio(BACKGROUND_SONG, overlay1, overlay2)
        temp_files.append(mixed_audio_path)

        # Add the mixed audio to the video
        output_video_path = add_audio_to_video(BACKGROUND_VIDEO_NO_MUSIC, mixed_audio_path)
        temp_files.append(output_video_path)

        # Generate unique destination blob name
        file_name = f"{sender[0].lower()}{recipient[0].lower()}{uuid.uuid4()}"
        destination_blob_name = f"videos/{file_name}.mp4"

        # Upload video to GCS
        video_url = upload_to_gcs(bucket, output_video_path, destination_blob_name)

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

@app.post("/motherqueen/audio/en-US/{recipient}")
async def upload_multiple_images(
    recipient: str
):
    temp_files = []  # Track temporary files for cleanup
    bucket = storage_client.bucket(MY_MOTHER_MY_QUEEN_BUCKET_NAME)

    try:
        # Generate audio clips
        hello_mother, happy_mothers_day = generate_my_mother_my_queen_clips(recipient)

        # Write audio data to temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio1, \
             tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio2:
            temp_audio1.write(b"".join(hello_mother))
            temp_audio2.write(b"".join(happy_mothers_day))
            temp_files.extend([temp_audio1.name, temp_audio2.name])

        # Upload audio files to GCS
        audio1_blob_name = f"audio/{recipient.lower()}_hello_mother_{uuid.uuid4()}.mp3"
        audio2_blob_name = f"audio/{recipient.lower()}_happy_mothers_day_{uuid.uuid4()}.mp3"
        audio1_url = upload_to_gcs(bucket, temp_audio1.name, audio1_blob_name)
        audio2_url = upload_to_gcs(bucket, temp_audio2.name, audio2_blob_name)

        return {
            "status": "success",
            "message": "My Mother My Queen audio resources created successfully",
            "audio1_url": audio1_url,
            "audio2_url": audio2_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.unlink(file_path)

@app.get("/")
def root():
    return {"message": "Welcome to the JOY API - we are going to do great!!!"}
