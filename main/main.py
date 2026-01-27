from fastapi import FastAPI
from .router import playlists, songs, auth, users, alt_names

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(songs.router)
app.include_router(alt_names.router)
app.include_router(playlists.router)

@app.get("/")
async def root():
    return {"message": "hello world"}



