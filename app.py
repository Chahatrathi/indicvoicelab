import asyncio
import os
import uuid
import time
import glob
from flask import Flask, render_template, request, send_file
import edge_tts
from deep_translator import GoogleTranslator

app = Flask(__name__)

# Detect environment
IS_VERCEL = "VERCEL" in os.environ
OUTPUT_DIR = "/tmp" if IS_VERCEL else os.path.join('static', 'outputs')

if not IS_VERCEL and not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

VOICES = {
    "hi-IN-MadhurNeural": {"name": "Hindi (Male)", "lang": "hi", "mic_code": "hi-IN"},
    "bn-IN-BashkarNeural": {"name": "Bengali (Male)", "lang": "bn", "mic_code": "bn-IN"},
    "gu-IN-NiranjanNeural": {"name": "Gujarati (Male)", "lang": "gu", "mic_code": "gu-IN"},
    "kn-IN-GaganNeural": {"name": "Kannada (Male)", "lang": "kn", "mic_code": "kn-IN"},
    "ml-IN-MidhunNeural": {"name": "Malayalam (Male)", "lang": "ml", "mic_code": "ml-IN"},
    "mr-IN-ManoharNeural": {"name": "Marathi (Male)", "lang": "mr", "mic_code": "mr-IN"},
    "pa-IN-HardikNeural": {"name": "Punjabi (Male)", "lang": "pa", "mic_code": "pa-IN"},
    "ta-IN-ValluvarNeural": {"name": "Tamil (Male)", "lang": "ta", "mic_code": "ta-IN"},
    "te-IN-MohanNeural": {"name": "Telugu (Male)", "lang": "te", "mic_code": "te-IN"},
    "en-IN-PrabhatNeural": {"name": "Indian English (Male)", "lang": "en", "mic_code": "en-IN"}
}

def cleanup_old_files():
    """Removes old voice files to prevent /tmp overflow."""
    now = time.time()
    for f in glob.glob(os.path.join(OUTPUT_DIR, "voice_*.mp3")):
        if os.stat(f).st_mtime < now - 600:  # Delete files older than 10 mins
            try: os.remove(f)
            except: pass

async def generate_speech(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

@app.route('/')
def index():
    return render_template('index.html', voices=VOICES)

@app.route('/get_audio/<filename>')
def get_audio(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        response = send_file(path, mimetype="audio/mpeg")
        # Prevent caching at the header level
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
    return "Not Found", 404

@app.route('/convert', methods=['POST'])
def convert():
    cleanup_old_files()
    input_text = request.form.get('text', '').strip()
    voice_key = request.form.get('voice')
    
    if not input_text:
        return "Input needed", 400

    target_lang = VOICES[voice_key]['lang']
    try:
        translated_text = GoogleTranslator(source='auto', target=target_lang).translate(input_text)
    except:
        translated_text = input_text 

    # Unique ID with timestamp ensures a totally fresh URL
    unique_name = f"voice_{uuid.uuid4().hex}_{int(time.time())}.mp3"
    filepath = os.path.join(OUTPUT_DIR, unique_name)

    try:
        asyncio.run(generate_speech(translated_text, voice_key, filepath))
        # Add a query param to the URL to double-ensure the browser doesn't cache
        audio_url = f"/get_audio/{unique_name}?v={int(time.time())}"
        
        return render_template('index.html', audio_path=audio_url, voices=VOICES, translated=translated_text)
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == '__main__':
    app.run()
