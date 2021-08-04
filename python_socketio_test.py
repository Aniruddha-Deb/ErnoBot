import asyncio
import socketio

sio = socketio.AsyncClient()

@sio.event(namespace="/bot")
async def connect():
    print('connection established')
    await sio.emit('pounce', 'team 2', callback=done, namespace='/bot')

@sio.event(namespace="/bot")
def disconnect():
    print('disconnected from server')

async def done():
    await sio.disconnect()

async def main():
    await sio.connect("http://localhost:5000", namespaces=['/bot'])
    await sio.wait()

if __name__ == "__main__":
    asyncio.run(main())
