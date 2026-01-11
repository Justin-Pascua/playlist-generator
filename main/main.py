from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "hello world"}


@app.get("/songs")
async def get_all_songs():
    return {"message": "no songs yet"}

@app.get("/playlists")
async def get_all_playlists():
    return {"message": "no playlists so far"}

@app.post("/playlists")
async def create_playlist(params):
    return {"playlist": "link here"}