import asyncio
import os
import uuid
import time
import glob
from flask import Flask, render_template, request, send_file, make_response
import edge_tts
from deep_translator import GoogleTranslator

app = Flask(__name__)

# Environment Configuration
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
        # Force the browser to treat this as a fresh stream every time
        response = make_response(send_file(path, mimetype="audio/mpeg"))
        response.headers["Content-Disposition"] = "inline; filename=voice.mp3"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return "Audio not ready, please refresh.", 404

@app.route('/convert', methods=['POST'])
def convert():
    # Cleanup old files before new generation
    for f in glob.glob(os.path.join(OUTPUT_DIR, "voice_*.mp3")):
        try:
            if os.path.getmtime(f) < time.time() - 300: # 5 mins
                os.remove(f)
        except: pass

    input_text = request.form.get('text', '').strip()
    voice_key = request.form.get('voice')
    
    if not input_text:
        return "Input empty", 400

    target_lang = VOICES[voice_key]['lang']
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(input_text)
    except:
        translated = input_text 

    # Generate strictly unique filename
    filename = f"voice_{uuid.uuid4().hex}_{int(time.time())}.mp3"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        asyncio.run(generate_speech(translated, voice_key, filepath))
        
        # Add cache buster to URL
        audio_url = f"/get_audio/{filename}?cb={uuid.uuid4().hex}"
        
        return render_template('index.html', 
                               audio_path=audio_url, 
                               voices=VOICES, 
                               translated=translated)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run()
