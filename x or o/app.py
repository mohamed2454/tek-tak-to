from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random, uuid, string
import os
if __name__ == "__main__":
    socketio = SocketIO(app)
    port = int(os.environ.get("PORT", 5000))  # يجيب البورت من Render أو يحط 5000 كـ default
    socketio.run(app, host="0.0.0.0", port=port)

app = Flask(__name__)
app.config['SECRET_KEY'] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

@app.route("/")
def index():
    return render_template("index.html")

def generate_room_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def new_room():
    return {
        "board": [["" for _ in range(3)] for _ in range(3)],
        "turn": "x",
        "winner": None,
        "players": {"x": None, "o": None},
    }

def check_winner(board):
    for r in range(3):
        if board[r][0] and board[r][0]==board[r][1]==board[r][2]:
            return board[r][0]
    for c in range(3):
        if board[0][c] and board[0][c]==board[1][c]==board[2][c]:
            return board[0][c]
    if board[0][0] and board[0][0]==board[1][1]==board[2][2]:
        return board[0][0]
    if board[0][2] and board[0][2]==board[1][1]==board[2][0]:
        return board[0][2]
    if all(board[r][c] for r in range(3) for c in range(3)):
        return "tie"
    return None

@socketio.on("create_room")
def create_room(data):
    rid = generate_room_code()
    while rid in rooms:
        rid = generate_room_code()
    rooms[rid] = new_room()
    join_room(rid)
    emit("room_created", {"room_id": rid}, to=request.sid)

@socketio.on("join_room")
def join_room_event(data):
    rid, role = data["room_id"], data.get("role","spectator").lower()
    if rid not in rooms:
        emit("error", {"msg":"Room not found"}, to=request.sid)
        return

    room = rooms[rid]
    join_room(rid)

    # assign player role
    if role in ["x","o"]:
        if room["players"][role] is None:
            room["players"][role] = request.sid
        else:
            role = "spectator"

    emit("state", {
        "board": room["board"],
        "turn": room["turn"],
        "winner": room["winner"],
        "players": {"x": bool(room["players"]["x"]), "o": bool(room["players"]["o"])},
        "your_role": role
    }, to=request.sid)

    emit("state", {
        "board": room["board"],
        "turn": room["turn"],
        "winner": room["winner"],
        "players": {"x": bool(room["players"]["x"]), "o": bool(room["players"]["o"])},
    }, room=rid)

@socketio.on("move")
def handle_move(data):
    rid, r, c = data["room_id"], data["row"], data["col"]
    room = rooms.get(rid)
    if not room: return
    if room["winner"]: return
    if room["board"][r][c] != "": return

    sid = request.sid
    player_symbol = room["turn"]

    if room["players"][player_symbol] != sid:
        return  # not your turn

    room["board"][r][c] = player_symbol
    room["winner"] = check_winner(room["board"])
    if not room["winner"]:
        room["turn"] = "o" if room["turn"]=="x" else "x"

    emit("state", {
        "board": room["board"],
        "turn": room["turn"],
        "winner": room["winner"],
        "players": {"x": bool(room["players"]["x"]), "o": bool(room["players"]["o"])},
    }, room=rid)
@socketio.on("chat_message")
def chat_message(data):
    rid, msg = data["room_id"], data["msg"]
    if rid in rooms:
        emit("chat_message", {"msg": msg}, room=rid)

@socketio.on("restart")
def restart(data):
    rid = data["room_id"]
    if rid in rooms:
        rooms[rid] = new_room()
        emit("state", {
            "board": rooms[rid]["board"],
            "turn": rooms[rid]["turn"],
            "winner": None,
            "players": {"x": bool(rooms[rid]["players"]["x"]), "o": bool(rooms[rid]["players"]["o"])},
        }, room=rid)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

