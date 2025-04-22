from elevenlabs.client import ElevenLabs
from manage_secrets import access_secret
import os

PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
ELEVENLABS_API_KEY = access_secret(PROJECT_ID, 'ELEVENLABS_API_KEY')
MAIN_VOICE_ID = access_secret(PROJECT_ID, 'MAIN_VOICE_ID')

def generate_good_moring_clips(sender: str, recipient: str):
    """Generates audio clips for a good morning message."""

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

def generate_my_mother_my_queen_clips(recipient: str):
    
    #VOICE = access_secret(PROJECT_ID, 'VOICE_Celeste_Vintage_Hollywood_Accent')
    VOICE = access_secret(PROJECT_ID, 'VOICE_DJ_MARATHON')
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    
    hello_mother = client.text_to_speech.convert(
        text=f"Hey {recipient},...This one is for you!",
        voice_id=VOICE,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    happy_mothers_day = client.text_to_speech.convert(
        text=f"Happy Mother’s Day {recipient}",
        voice_id=VOICE,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    
    return hello_mother, happy_mothers_day 

def generate_audio(message: str, voice_id: str):
    """Generates audio using ElevenLabs API."""

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    audio = client.text_to_speech.convert(
        text=message,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    return audio
