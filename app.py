import asyncio
import os
import uuid
import glob
from flask import Flask, render_template, request, send_file
import edge_tts
from deep_translator import GoogleTranslator

app = Flask(__name__)

# Determine if we are running on Vercel or locally
# Vercel provides a read-only filesystem except for /tmp
IS_VERCEL = "VERCEL" in os.environ

if IS_VERCEL:
    OUTPUT_DIR = "/tmp"
else:
    OUTPUT_DIR = os.path.join('static', 'outputs')
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

# Voice configuration dictionary
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

# Special route to serve the audio file from /tmp on Vercel
@app.route('/get_audio/<filename>')
def get_audio(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename))

@app.route('/convert', methods=['POST'])
def convert():
    input_text = request.form.get('text', '').strip()
    voice_key = request.form.get('voice')
    
    if not input_text:
        return "Please enter text.", 400

    target_lang = VOICES[voice_key]['lang']
    try:
        translated_text = GoogleTranslator(source='auto', target=target_lang).translate(input_text)
    except Exception as e:
        print(f"Translation Error: {e}")
        translated_text = input_text 

    # Cleanup old files (Only works locally; /tmp cleans itself on Vercel)
    if not IS_VERCEL:
        for f in glob.glob(os.path.join(OUTPUT_DIR, "*.mp3")):
            try: os.remove(f)
            except: continue

    filename = f"voice_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        # Generate the audio
        asyncio.run(generate_speech(translated_text, voice_key, filepath))
        
        # On Vercel, we point to our custom route; locally we use the static folder
        if IS_VERCEL:
            audio_url = f"/get_audio/{filename}"
        else:
            audio_url = f"/static/outputs/{filename}"

        return render_template('index.html', 
                               audio_path=audio_url, 
                               voices=VOICES, 
                               translated=translated_text)
                               
    except Exception as e:
        return f"Note: Vercel requires persistent storage for long-term file saving. Error: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)