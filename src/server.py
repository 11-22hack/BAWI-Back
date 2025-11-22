import os, dotenv
import pprint
dotenv.load_dotenv()

import uvicorn
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from utils.navigate import navigate
from utils.find_matching import find_matching
from utils.interpolate_images import interpolate_images


##############################################################################

HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DATA_DIR = os.getenv("DATA_DIR")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

cache: dict[str, str] = {}

##############################################################################


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def gen_video(path_segments: list[list[float, float, float]], cache_key: str):
    global cache

    matching_images = find_matching(path_segments, os.path.join(DATA_DIR, "images"))
    pprint.pprint(matching_images)
    interpolate_images(
        image_paths=[os.path.join(DATA_DIR, "images", image) for image in matching_images],
        out_file=f"{cache_key}.mp4",
        out_dir=os.path.join(DATA_DIR, "cache")
    )

    cache[cache_key] = os.path.join(DATA_DIR, "cache", f"{cache_key}.mp4")


@app.get("/get-meta")
def get_meta(startLat: str, startLng: str, endLat: str, endLng: str):
    cache_key = f"{startLng},{startLat},{endLng},{endLat}"
    start_point = (startLng, startLat)
    end_point = (endLng, endLat)

    if cache_key in cache and cache[cache_key] != "-1":
        return {
            "key": cache_key,
            "result": navigate(start_point, end_point),
        }

    if cache_key in cache:
        raise HTTPException(status_code=201, detail="In Progress")

    raise HTTPException(status_code=400, detail="invalid request")


@app.get("/gen-video")
def navigate_endpoint(startLat: str, startLng: str, endLat: str, endLng: str):
    cache_key = f"{startLng},{startLat},{endLng},{endLat}"

    if cache.get(cache_key):
        if cache[cache_key] == "-1":
            raise HTTPException(status_code=201, detail="In progress")
        else:
            return FileResponse(cache[cache_key])

    if os.path.exists(os.path.join(DATA_DIR, "cache", f"{cache_key}.mp4")):
        cache[cache_key] = os.path.join(DATA_DIR, "cache", f"{cache_key}.mp4")
        return FileResponse(cache[cache_key])

    start_point = (startLng, startLat)
    end_point = (endLng, endLat)

    result = navigate(start_point, end_point)
    path_segments = result["path"]

    cache[cache_key] = "-1"
    threading.Thread(
        target=gen_video,
        args=(path_segments, cache_key),
    ).start()

    return {
        "key": cache_key,
        "result": result,
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host=HOST, port=int(PORT), reload=True)
