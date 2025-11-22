import math
import pprint
import requests, os, dotenv
dotenv.load_dotenv()


TMAP_APP_KEY = os.getenv("TMAP_APP_KEY")


def _get_distance(a: tuple[float, float], b: tuple[float, float]):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)


def _extract_points(item, result: list[tuple[float, float]]):
    if (isinstance(item, list)
        and len(item) == 2
        and all(isinstance(v, (int, float)) for v in item)):
        result.append((item[0], item[1]))
        return

    if isinstance(item, list):
        for sub in item:
            _extract_points(sub, result)


def navigate(start: tuple[str, str], end: tuple[str, str]):
    res = requests.post(
        "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json&callback=result",
        headers={
            "appKey": TMAP_APP_KEY,
        },
        data={
            "startX" : start[0],
            "startY" : start[1],
            "endX" : end[0],
            "endY" : end[1],
            "reqCoordType" : "WGS84GEO",
            "resCoordType" : "WGS84GEO",
            "startName" : "출발지",
            "endName" : "도착지",
        }
    ).json()

    coords = []
    for path in res.get("features", []):
        _extract_points(path.get("geometry", {}).get("coordinates", []), coords)

    result = []
    for coord in coords:
        if (
            result
            and result[-1][0] == coord[0]
            and result[-1][1] == coord[1]
        ): continue

        if len(result) < 2:
            result.append(list(coord))
            continue

        distance = _get_distance(result[-1], coord)
        if distance > 0.0001:
            segments = int(distance / 0.0001)
            for i in range(1, segments):
                result.append([
                    result[-1][0] + (coord[0] - result[-1][0]) * i / segments,
                    result[-1][1] + (coord[1] - result[-1][1]) * i / segments,
                ])

        result.append(list(coord))

    for i in range(1, len(result)):
        direction = (result[i][0] - result[i-1][0], result[i][1] - result[i-1][1])
        degree = math.atan2(direction[1], direction[0]) * 180 / math.pi
        result[i-1].append(degree)

    return {
        "path": result,
        "raw": res.get("features", []),
    }

if __name__ == "__main__":
    print("Test for utils.navigate")
    pprint.pprint(
        navigate(
            ("126.99696349525492", "37.561590999574236"),
            ("126.9956203528817", "37.56216145788358")
        )
    )