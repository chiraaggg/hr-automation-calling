import os
import asyncio
import websockets
import json
import base64
from divya_prompt import parse_candidate_response

PORT = int(os.getenv("PORT", 8765))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def handle_stream(websocket):
    async for message in websocket:
        data = json.loads(message)
        if data.get("event") == "media":
            audio_b64 = data["media"]["payload"]
            audio_bytes = base64.b64decode(audio_b64)

            # Send audio_bytes to OpenAI Realtime via proper WebSocket flow
            # Receive AI audio and transcript
            ai_audio_bytes = b"... processed AI audio ..."
            transcript_text = "... processed transcript ..."

            await websocket.send(json.dumps({
                "event": "media",
                "media": {"payload": base64.b64encode(ai_audio_bytes).decode("utf-8")}
            }))

            candidate_info = parse_candidate_response(transcript_text)
            print("Candidate info:", candidate_info)

        elif data.get("event") == "start":
            print("Stream started")
        elif data.get("event") == "stop":
            print("Stream stopped")

async def main():
    async with websockets.serve(handle_stream, "0.0.0.0", PORT):
        print(f"WebSocket server listening on port {PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
