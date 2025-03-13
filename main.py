from fastapi import FastAPI
from fastapi import FastAPI, HTTPException
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
import tempfile
import os
from starlette.responses import FileResponse

app = FastAPI()

# Configuration
ELEVENLABS_API_KEY = 'sk_18899df01808bfbd6a7d51150732740481895233be7b4385'
VOICE_ID = 'tcO8jJ1XXzdQ4pzViV9c'
BACKGROUND_SONG = "resources/good_morning_i_love_you_blank.mp3" 

def generate_audio_clips(sender: str, recipient: str):
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    
    hi_recipient = client.text_to_speech.convert(
        text=f"Hi {recipient}",
        voice_id=VOICE_ID,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    sender_loves_recipient = client.text_to_speech.convert(
        text=f"{sender} loves you {recipient}",
        voice_id=VOICE_ID,
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

@app.post("/goodmorning/music/en-US/{sender}/{recipient}")
async def create_greeting(
    sender: str,
    recipient: str
):
    try:
        # Generate audio clips
        overlay1, overlay2 = generate_audio_clips(sender, recipient)
        
        # Mix audio
        output_path = mix_audio(BACKGROUND_SONG, overlay1, overlay2)
        
        # Return the file and clean up
        response = FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename="goodmorning.mp3"
        )
        
        # Schedule cleanup
        response.background = lambda: os.unlink(output_path)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Welcome to the JOY API - we are going to do great!!!"}
