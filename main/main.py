from fastapi import FastAPI
from .router import model, playlists, songs

# initialization process:
# - load model
# - check db
# - maybe ping YouTube API?

app = FastAPI()

app.include_router(model.router)
app.include_router(playlists.router)
app.include_router(songs.router)

@app.get("/")
async def root():
    return {"message": "hello world"}



