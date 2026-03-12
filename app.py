import asyncio
import os
import uuid
import glob
from flask import Flask, render_template, request
import edge_tts
from googletrans import Translator

app = Flask(__name__)
translator = Translator()

# Ensure directories exist
OUTPUT_DIR = os.path.join('static', 'outputs')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Voice list with mapping to ISO language codes for translation
VOICES = {
    "hi-IN-MadhurNeural": {"name": "Hindi (Male)", "lang": "hi"},
    "hi-IN-SwararaNeural": {"name": "Hindi (Female)", "lang": "hi"},
    "bn-IN-BashkarNeural": {"name": "Bengali (Male)", "lang": "bn"},
    "bn-IN-TanishaNeural": {"name": "Bengali (Female)", "lang": "bn"},
    "gu-IN-NiranjanNeural": {"name": "Gujarati (Male)", "lang": "gu"},
    "gu-IN-DhwaniNeural": {"name": "Gujarati (Female)", "lang": "gu"},
    "kn-IN-GaganNeural": {"name": "Kannada (Male)", "lang": "kn"},
    "kn-IN-SapnaNeural": {"name": "Kannada (Female)", "lang": "kn"},
    "ml-IN-MidhunNeural": {"name": "Malayalam (Male)", "lang": "ml"},
    "ml-IN-SobhanaNeural": {"name": "Malayalam (Female)", "lang": "ml"},
    "mr-IN-ManoharNeural": {"name": "Marathi (Male)", "lang": "mr"},
    "mr-IN-AarohiNeural": {"name": "Marathi (Female)", "lang": "mr"},
    "pa-IN-HardikNeural": {"name": "Punjabi (Male)", "lang": "pa"},
    "pa-IN-OjasNeural": {"name": "Punjabi (Female)", "lang": "pa"},
    "ta-IN-ValluvarNeural": {"name": "Tamil (Male)", "lang": "ta"},
    "ta-IN-PallaviNeural": {"name": "Tamil (Female)", "lang": "ta"},
    "te-IN-MohanNeural": {"name": "Telugu (Male)", "lang": "te"},
    "te-IN-ShrutiNeural": {"name": "Telugu (Female)", "lang": "te"},
    "en-IN-PrabhatNeural": {"name": "Indian English (Male)", "lang": "en"},
    "en-IN-NeerjaNeural": {"name": "Indian English (Female)", "lang": "en"}
}

async def generate_speech(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

@app.route('/')
def index():
    return render_template('index.html', voices=VOICES)

@app.route('/convert', methods=['POST'])
def convert():
    input_text = request.form.get('text', '').strip()
    voice_key = request.form.get('voice')
    
    if not input_text:
        return "Please enter text.", 400

    # 1. TRANSLATION LOGIC
    # Get the target language code from our VOICES dictionary
    target_lang = VOICES[voice_key]['lang']
    try:
        translated = translator.translate(input_text, dest=target_lang)
        final_text = translated.text
    except Exception as e:
        print(f"Translation failed: {e}")
        final_text = input_text # Fallback to original text

    # 2. CLEANUP
    old_files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp3"))
    for f in old_files:
        try:
            os.remove(f)
        except:
            continue

    # 3. GENERATE AUDIO
    filename = f"voice_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        asyncio.run(generate_speech(final_text, voice_key, filepath))
        return render_template('index.html', 
                               audio=filename, 
                               voices=VOICES, 
                               original=input_text, 
                               translated=final_text)
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)