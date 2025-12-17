
import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/api/v1/recording/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send start message
            start_msg = {
                "type": "start",
                "url": "https://example.com"
            }
            await websocket.send(json.dumps(start_msg))
            print("Sent start message")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received response: {response}")
            
            # Send stop message
            stop_msg = {
                "type": "stop"
            }
            await websocket.send(json.dumps(stop_msg))
            print("Sent stop message")
            
            response = await websocket.recv()
            print(f"Received response: {response}")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
