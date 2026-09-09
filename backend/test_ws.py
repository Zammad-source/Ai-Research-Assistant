import asyncio
import websockets
import json

async def user_a():
    uri = "ws://127.0.0.1:8000/translator/ws/room1?target_lang=ur-roman"
    async with websockets.connect(uri) as ws:
        await asyncio.sleep(1)
        await ws.send(json.dumps({"text": "kya haal hai"}))
        await asyncio.sleep(3)

async def user_b():
    uri = "ws://127.0.0.1:8000/translator/ws/room1?target_lang=en"
    async with websockets.connect(uri) as ws:
        response = await ws.recv()
        print("User B received:", response)

async def main():
    await asyncio.gather(user_a(), user_b())

asyncio.run(main())