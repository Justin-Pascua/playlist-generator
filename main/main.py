from fastapi import FastAPI
from .router import model, playlists, songs, auth, users

# initialization process:
# - load model
# - check db
# - maybe ping YouTube API?

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(songs.router)
app.include_router(playlists.router)
app.include_router(model.router)

@app.get("/")
async def root():
    return {"message": "hello world"}



