import os
import time
import execution
import asyncio
from typing import List, Literal, NamedTuple, Optional
from server import PromptServer
from aiohttp import web

routes = PromptServer.instance.routes


old_task_done = execution.PromptQueue.task_done


play_type = "all"
video_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "video")


def new_task_done(
    self, item_id, history_result, status: Optional["PromptQueue.ExecutionStatus"], **kwargs
):

    ret = old_task_done(self, item_id, history_result, status, **kwargs),
    if play_type == "all" and len(self.queue) > 0:
        return ret

    PromptServer.instance.send_sync("pc.play_ding_dong_audio", {
        "status": status.status_str
    })

    return ret


execution.PromptQueue.task_done = new_task_done


files_end_with = (".mp4", ".avi", ".mov", ".mkv", ".webm", ".mp3", ".wav")


def load_video():
    if not os.path.exists(video_dir):
        return []

    video_files = []
    for file in os.listdir(video_dir):
        if file.lower().endswith(files_end_with):
            video_files.append(file)

    return video_files


local_video_files = load_video()




@routes.post("/pc_get_video_files")
async def get_video_files(request):
    global local_video_files
    local_video_files = load_video()
    return web.json_response({"video_files": local_video_files})


@routes.get("/pc_get_audio")
async def get_audio(request):
    filename = request.query.get("filename")
    if not filename:
        return web.Response(text="No filename provided", status=400)

    audio_path = os.path.join(video_dir, filename)

    if not os.path.exists(audio_path):
        return web.Response(text="Audio file not found", status=404)

    if not filename.lower().endswith(files_end_with):
        return web.Response(text="Invalid audio file format", status=400)

    return web.FileResponse(audio_path)


@routes.post("/pc_set_play_type")
async def set_play_type(request):
    global play_type
    the_data = await request.post()
    play_type = the_data.get("play_type", "all")
    return web.json_response({})


# Handle file upload via aiohttp
@routes.post("/pc_upload_video")
async def upload_video(request):
    reader = await request.multipart()
    field = await reader.next()

    if not field or field.name != "file":
        return web.json_response({"error": "No file uploaded"}, status=400)

    filename = field.filename
    if not filename.lower().endswith(files_end_with):
        return web.json_response({"error": "Invalid file format"}, status=400)

    # Save uploaded file
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)

    file_path = os.path.join(video_dir, filename)

    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

    return web.json_response({"success": True, "filename": filename})


class EatAny(str):
    def __init__(self):
        pass

    def __eq__(self, _):
        return True

    def __ne__(self, _):
        return False


any_type = EatAny()


class DingDong:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "music": (
                    local_video_files,
                    {
                        "default": (
                            local_video_files[0] if len(local_video_files) > 0 else None
                        )
                    },
                ),
                "volume": ("FLOAT", {"default": 100, "min": 0, "max": 100, "step": 1}),
                "anything": (any_type, {}),
            },
        }

    OUTPUT_NODE = True
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "ding_dong"
    CATEGORY = "😱 PointAgiClub"

    def ding_dong(self, volume, music, anything):
        PromptServer.instance.send_sync(
            "pc.play_ding_dong_mui", {"volume": volume, "music": music}
        )
        return (anything,)


class TimeSleep:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seconds": ("FLOAT", {"default": 1, "min": 0, "max": 10, "step": 0.1}),
            },
            "optional": {
                "anything": (any_type,),
            },
        }

    OUTPUT_NODE = True
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "sleep"
    CATEGORY = "😱 PointAgiClub"

    def sleep(self, seconds, **anything):
        time.sleep(seconds)
        return (anything,)


class DingDongText:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"default": "Hello, World!"}),
                "pitch": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.1},
                ),
                "rate": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1},
                ),
                "volume": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.1},
                ),
                "anything": (any_type, {}),
            },
        }

    OUTPUT_NODE = True
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "ding_dong"
    CATEGORY = "😱 PointAgiClub"

    def ding_dong(self, text, pitch, rate, volume, anything):

        PromptServer.instance.send_sync(
            "pc.play_ding_dong_text",
            {"text": text, "pitch": pitch, "rate": rate, "volume": volume},
        )

        return (anything,)


NODE_CLASS_MAPPINGS = {
    "pc ding dong": DingDong,
    "pc ding dong text": DingDongText,
    "pc time sleep": TimeSleep,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "pc ding dong": "⏰Ding Dong",
    "pc ding dong text": "⏰Ding Dong Text",
    "pc time sleep": "⏰Time Sleep",
}
WEB_DIRECTORY = "./web"
