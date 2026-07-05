import os
import time
import execution
import logging
from pathlib import Path
from server import PromptServer
from aiohttp import web

routes = PromptServer.instance.routes


old_task_done = execution.PromptQueue.task_done


play_type = "all"
batch_failed = False
video_dir = Path(__file__).resolve().parent / "video"
default_music = "ringtone1.mp3"


def _queue_has_pending_work(prompt_queue):
    try:
        with prompt_queue.mutex:
            return bool(prompt_queue.queue) or bool(prompt_queue.currently_running)
    except Exception:
        return bool(getattr(prompt_queue, "queue", [])) or bool(
            getattr(prompt_queue, "currently_running", {})
        )


def new_task_done(*args, **kwargs):
    global batch_failed

    prompt_queue = args[0] if args else None
    status = kwargs.get("status")
    if status is None and len(args) >= 4:
        status = args[3]

    ret = old_task_done(*args, **kwargs)

    try:
        status_str = getattr(status, "status_str", None)
        if play_type == "all" and status_str == "error":
            batch_failed = True

        if play_type == "all" and prompt_queue is not None and _queue_has_pending_work(
            prompt_queue
        ):
            return ret

        if play_type == "all" and batch_failed:
            status_str = "error"
            batch_failed = False

        if status_str:
            PromptServer.instance.send_sync(
                "pc.play_ding_dong_audio", {"status": status_str}
            )
    except Exception:
        logging.exception("Failed to send ding-dong completion event")

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

    return sorted(video_files, key=str.casefold)


local_video_files = load_video()


def get_default_music():
    if default_music in local_video_files:
        return default_music
    return local_video_files[0] if len(local_video_files) > 0 else None


def get_safe_video_path(filename):
    if not filename or not isinstance(filename, str):
        return None
    if filename != os.path.basename(filename) or "\\" in filename:
        return None
    if not filename.lower().endswith(files_end_with):
        return None

    path = (video_dir / filename).resolve()
    video_root = video_dir.resolve()
    try:
        path.relative_to(video_root)
    except ValueError:
        return None

    return path


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

    audio_path = get_safe_video_path(filename)
    if audio_path is None:
        return web.Response(text="Invalid audio filename or format", status=400)

    if not os.path.exists(audio_path):
        return web.Response(text="Audio file not found", status=404)

    return web.FileResponse(audio_path)


@routes.post("/pc_set_play_type")
async def set_play_type(request):
    global play_type, batch_failed
    the_data = await request.post()
    play_type = the_data.get("play_type", "all")
    if play_type not in {"all", "one"}:
        play_type = "all"
    batch_failed = False
    return web.json_response({})


# Handle file upload via aiohttp
@routes.post("/pc_upload_video")
async def upload_video(request):
    global local_video_files

    reader = await request.multipart()
    field = await reader.next()

    if not field or field.name != "file":
        return web.json_response({"error": "No file uploaded"}, status=400)

    filename = field.filename
    file_path = get_safe_video_path(filename)
    if file_path is None:
        return web.json_response({"error": "Invalid file format"}, status=400)

    video_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

    local_video_files = load_video()

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
                    {"default": get_default_music()},
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
