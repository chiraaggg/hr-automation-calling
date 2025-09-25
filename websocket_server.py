import asyncio
import websockets
import json
import base64
import io
from pydub import AudioSegment
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 8765))
openai = OpenAI(api_key=OPENAI_API_KEY)

# Convert AI audio to PCM 16-bit mono 8kHz for Twilio
def convert_to_pcm(audio_bytes):
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_channels(1).set_frame_rate(8000).set_sample_width(2)
    return audio.raw_data

async def handle_stream(websocket):
    async for message in websocket:
        data = json.loads(message)

        if data.get("event") == "media":
            audio_b64 = data["media"]["payload"]
            audio_bytes = base64.b64decode(audio_b64)

            # 1️⃣ Transcribe candidate audio
            transcript_resp = await openai.audio.transcriptions.create(
                file=io.BytesIO(audio_bytes),
                model="whisper-1"
            )
            transcript_text = transcript_resp.text

            # 2️⃣ Generate AI response
            ai_resp = await openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":f"Candidate said: {transcript_text}\nRespond as Divya."}]
            )
            ai_text = ai_resp.choices[0].message.content

            # 3️⃣ TTS
            tts_resp = await openai.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=ai_text
            )
            ai_audio_bytes = tts_resp.read()

            # 4️⃣ Convert to PCM
            pcm_bytes = convert_to_pcm(ai_audio_bytes)

            # 5️⃣ Send back to Twilio
            await websocket.send(json.dumps({
                "event": "media",
                "media": {"payload": base64.b64encode(pcm_bytes).decode("utf-8")}
            }))

        elif data.get("event") == "start":
            print("Stream started")
        elif data.get("event") == "stop":
            print("Stream stopped")

async def main():
    async with websockets.serve(handle_stream, "0.0.0.0", PORT):
        print(f"WebSocket server listening on port {PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
