```python
import socketio
import uvicorn
from fastapi import FastAPI
import chess

# Initialize FastAPI and Socket.IO
app = FastAPI()
sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
socket_app = socketio.ASGIApp(sio, app)

# Store rooms and their data
rooms = {}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    for room_id, room_data in list(rooms.items()):
        if sid in room_data["players"]:
            room_data["players"].remove(sid)
            await sio.emit("opponent_disconnected", room=room_id)
            if not room_data["players"]:
                del rooms[room_id]
            break

@sio.event
async def join_room(sid, data):
    room_id = data["room_id"]
    if room_id not in rooms:
        # Create new room
        rooms[room_id] = {
            "players": [sid],
            "board": chess.Board(),
            "game_state": {"status": "Waiting for opponent..."}
        }
        await sio.enter_room(sid, room_id)
        await sio.emit("player_assignment", {"color": "white"}, to=sid)
        print(f"Player {sid} joined room {room_id} as white")
    elif len(rooms[room_id]["players"]) == 1:
        # Second player joins
        rooms[room_id]["players"].append(sid)
        await sio.enter_room(sid, room_id)
        await sio.emit("player_assignment", {"color": "black"}, to=sid)
        await sio.emit("opponent_joined", room=room_id)
        print(f"Player {sid} joined room {room_id} as black")
    else:
        await sio.emit("room_full", {"message": "This room is full."}, to=sid)

@sio.event
async def move(sid, data):
    room_id = data["room_id"]
    move_san = data["move"]
    if room_id in rooms:
        board = rooms[room_id]["board"]
        try:
            move = board.parse_san(move_san)
            board.push(move)
            await sio.emit("move", {"move": move_san, "fen": board.fen()}, room=room_id)
            # Update game status
            status = "White's turn" if board.turn == chess.WHITE else "Black's turn"
            if board.is_checkmate():
                status = f"Checkmate! {'Black' if board.turn == chess.WHITE else 'White'} wins!"
            elif board.is_stalemate():
                status = "Game over: Stalemate!"
            elif board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
                status = "Game over: Draw!"
            elif board.is_check():
                status = f"Check! {status}"
            rooms[room_id]["game_state"]["status"] = status
            await sio.emit("game_status", {"status": status}, room=room_id)
        except ValueError:
            await sio.emit("invalid_move", {"message": "Invalid move"}, to=sid)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
```
