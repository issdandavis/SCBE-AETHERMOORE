# FastAPI

FastAPI is a modern, high-performance Python web framework for building APIs based on standard Python type hints. It is built on Starlette for the web layer and Pydantic for data validation, providing automatic OpenAPI documentation and async support.

## Dependency Injection

FastAPI's dependency injection system declares reusable components resolved at request time:

```python
from fastapi import FastAPI, Depends, Query
from typing import Annotated

app = FastAPI()

async def common_parameters(
    q: str | None = None, skip: int = 0,
    limit: int = Query(default=100, le=1000)
):
    return {"q": q, "skip": skip, "limit": limit}

CommonParams = Annotated[dict, Depends(common_parameters)]

@app.get("/items/")
async def read_items(commons: CommonParams):
    return commons

# Yield dependency (context manager pattern)
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items/{item_id}")
async def read_item(item_id: int, db = Depends(get_db)):
    return db.query(Item).get(item_id)

# Nested dependencies
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_active_user)):
    return current_user
```

## Authentication via Cookies and Tokens

Implement authentication using OAuth2 bearer tokens and HTTP cookies:

```python
from fastapi import FastAPI, Depends, HTTPException, status, Cookie, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import jwt

app = FastAPI()
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return get_user(username)

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=30))
    return Token(access_token=token, token_type="bearer")

# Cookie-based authentication
@app.post("/login")
async def login_cookie(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.username})
    response.set_cookie(
        key="access_token", value=f"Bearer {token}",
        httponly=True, secure=True, samesite="lax", max_age=1800,
    )
    return {"message": "Login successful"}

async def get_user_from_cookie(access_token: str | None = Cookie(default=None)):
    if not access_token or not access_token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = access_token.replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return get_user(payload.get("sub"))

@app.get("/dashboard")
async def dashboard(user = Depends(get_user_from_cookie)):
    return {"message": f"Welcome {user.username}"}
```

## Error Handling

Handle errors with HTTPException and custom exception handlers:

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI()

# Basic HTTPException
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found",
                            headers={"X-Error": "Item lookup failed"})
    return items_db[item_id]

# Custom exception class
class ItemNotFoundError(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id

@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "message": f"Item {exc.item_id} does not exist"},
    )

# Override validation error handler
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": " -> ".join(str(l) for l in e["loc"]),
               "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "validation_error", "details": errors})

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = items_db.get(item_id)
    if not item:
        raise ItemNotFoundError(item_id)
    return item
```

## WebSocket Endpoints with Dependencies

Build real-time WebSocket endpoints with dependency injection and broadcasting:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, status

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for conn in self.active_connections:
            await conn.send_text(message)

manager = ConnectionManager()

async def get_ws_user(websocket: WebSocket, token: str = Query(default=None)):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    user = verify_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return user

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str, user=Depends(get_ws_user)):
    if user is None:
        return
    await manager.connect(websocket)
    await manager.broadcast(f"{user.username} joined {room_id}")
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"{user.username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"{user.username} left {room_id}")

@app.websocket("/ws/json")
async def websocket_json(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"type": "response", "echo": data})
    except WebSocketDisconnect:
        pass
```
