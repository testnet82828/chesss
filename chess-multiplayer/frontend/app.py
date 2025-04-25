```python
import streamlit as st
import chess
import socketio
import random
import string
from streamlit.components.v1 import html

# Initialize Socket.IO client
sio = socketio.Client()

# Streamlit app
st.title("Multiplayer Chess")

# Get room ID from query params or generate new one
query_params = st.experimental_get_query_params()
room_id = query_params.get("room", [None])[0]
if not room_id:
    room_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    st.experimental_set_query_params(room=room_id)

# Session state to store game data
if "board" not in st.session_state:
    st.session_state.board = chess.Board()
if "player_color" not in st.session_state:
    st.session_state.player_color = None
if "game_status" not in st.session_state:
    st.session_state.game_status = "Waiting for opponent..."
if "opponent_joined" not in st.session_state:
    st.session_state.opponent_joined = False
if "fen" not in st.session_state:
    st.session_state.fen = st.session_state.board.fen()

# Generate shareable link (update with your Netlify URL after deployment)
share_link = f"https://your-site.netlify.app/?room={room_id}"
if not st.session_state.opponent_joined:
    if st.button("Generate Share Link"):
        st.write(f"Share this link with a friend: [{share_link}]({share_link})")
        st.write("Link copied to clipboard!")
        st.write('<script>navigator.clipboard.writeText("' + share_link + '")</script>', unsafe_allow_html=True)

# Socket.IO event handlers
@sio.event
def connect():
    sio.emit("join_room", {"room_id": room_id})

@sio.event
def player_assignment(data):
    st.session_state.player_color = data["color"]
    st.session_state.game_status = f"You are playing as {data['color']}"
    st.rerun()

@sio.event
def opponent_joined():
    st.session_state.opponent_joined = True
    st.session_state.game_status = "Opponent joined! Your move if you are white."
    st.rerun()

@sio.event
def move(data):
    move_san = data["move"]
    st.session_state.board.push_san(move_san)
    st.session_state.fen = data["fen"]
    st.rerun()

@sio.event
def game_status(data):
    st.session_state.game_status = data["status"]
    st.rerun()

@sio.event
def invalid_move(data):
    st.session_state.game_status = data["message"]
    st.rerun()

@sio.event
def opponent_disconnected():
    st.session_state.opponent_joined = False
    st.session_state.game_status = "Opponent disconnected. Waiting for a new opponent..."
    st.rerun()

@sio.event
def room_full(data):
    st.session_state.game_status = data["message"]
    st.rerun()

# Connect to the backend (update with Render URL after deployment)
if not sio.connected:
    try:
        sio.connect("https://your-render-backend.onrender.com")  # Update with Render URL
    except Exception as e:
        st.error(f"Failed to connect to server: {e}")

# Render chessboard using chessboard.js
board_html = f"""
<div id="board" style="width: 400px; margin: auto;"></div>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.2/chess.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css" />
<script>
    var board = Chessboard('board', {{
        position: '{st.session_state.fen}',
        orientation: '{st.session_state.player_color or "white"}',
        draggable: true,
        onDrop: function(source, target) {{
            var move = {{from: source, to: target, promotion: 'q'}};
            fetch('/make_move', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{room_id: '{room_id}', move: move}})
            }}).then(response => response.json()).then(data => {{
                if (data.error) alert(data.error);
            }});
        }}
    }});
</script>
"""
html(board_html, height=450)

# Move input (backup for manual entry)
move = st.text_input("Enter move (e.g., e4):")
if st.button("Make Move"):
    if move:
        sio.emit("move", {"room_id": room_id, "move": move})

# Display game status
st.write(st.session_state.game_status)
```
