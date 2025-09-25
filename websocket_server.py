import asyncio
import websockets
import json
import base64
import io
import os
import subprocess
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 8765))
openai = OpenAI(api_key=OPENAI_API_KEY)

# Convert any audio bytes to PCM 16-bit mono 8kHz using ffmpeg
def convert_to_pcm(audio_bytes):
    process = subprocess.run(
        [
            "ffmpeg",
            "-i", "pipe:0",
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "8000",
            "pipe:1"
        ],
        input=audio_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    return process.stdout

# Send audio in small chunks (~20ms per chunk)
async def send_pcm_chunks(ws, pcm_bytes):
    CHUNK_SIZE = 320  # 20ms @ 8kHz, 16-bit mono
    for i in range(0, len(pcm_bytes), CHUNK_SIZE):
        chunk = pcm_bytes[i:i+CHUNK_SIZE]
        await ws.send(json.dumps({
            "event": "media",
            "media": {"payload": base64.b64encode(chunk).decode("utf-8")}
        }))

async def handle_stream(websocket):
    async for message in websocket:
        data = json.loads(message)

        if data.get("event") == "start":
            print("Stream started")
            # Send a short greeting immediately to prevent Twilio from cutting
            greeting_resp = await openai.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input="Hello, this is Divya from Hire AI. Please wait while I connect."
            )
            greeting_pcm = convert_to_pcm(greeting_resp.read())
            await send_pcm_chunks(websocket, greeting_pcm)

        elif data.get("event") == "media":
            audio_b64 = data["media"]["payload"]
            audio_bytes = base64.b64decode(audio_b64)

            # 1️⃣ Transcribe candidate audio
            try:
                transcript_resp = await openai.audio.transcriptions.create(
                    file=io.BytesIO(audio_bytes),
                    model="whisper-1"
                )
                transcript_text = transcript_resp.text
            except Exception as e:
                print("Transcription error:", e)
                continue

            # 2️⃣ Generate AI response
            try:
                ai_resp = await openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":f"Candidate said: {transcript_text}\nRespond as Divya."}]
                )
                ai_text = ai_resp.choices[0].message.content
            except Exception as e:
                print("AI generation error:", e)
                continue

            # 3️⃣ Convert AI text to speech
            try:
                tts_resp = await openai.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice="alloy",
                    input=ai_text
                )
                ai_audio_bytes = tts_resp.read()
            except Exception as e:
                print("TTS error:", e)
                continue

            # 4️⃣ Convert to PCM for Twilio
            pcm_bytes = convert_to_pcm(ai_audio_bytes)

            # 5️⃣ Stream PCM audio in small chunks
            await send_pcm_chunks(websocket, pcm_bytes)

        elif data.get("event") == "stop":
            print("Stream stopped")

async def main():
    async with websockets.serve(handle_stream, "0.0.0.0", PORT):
        print(f"WebSocket server listening on port {PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
