import os
import re
import random
from datetime import timedelta

from django.db.models import Max
from django.http import Http404, JsonResponse
from furja.celery import app as celery_app

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .models import Video
from .tasks import download

from dotenv import load_dotenv
from isodate import parse_duration


load_dotenv()

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
YOUTUBE = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)


def extract_video_id(url):
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)

    if match:
        return match.group(1)

    return None


def get_random_sample(size=18, exclude_video_id=None):
    videos = Video.objects.all()

    if exclude_video_id:
        videos = videos.exclude(id=exclude_video_id)

    videos = list(videos.order_by('?'))  # Order randomly

    return videos[:size]


def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    output = []

    if hours:
        output.append(hours)

    output += [minutes, seconds]

    return ':'.join([f"{int(i):02}" for i in output])


def parse_duration_to_iso8601(duration_str):
    iso8601_duration = "PT"
    time_parts = [int(part) for part in duration_str.split(':')]

    if len(time_parts) == 2:
        p = ['M', 'S']
    else:
        p = ['H', 'M', 'S']

    for i, j in zip(time_parts, p):
        if not i:
            continue
        iso8601_duration += f"{i}{j}"

    return iso8601_duration


def get_video_info_from_api(video_id):
    def get_thumb(thumbnails):
        st = thumbnails.get('standard')
        if st:
            return st['url']
        else:
            return thumbnails['high']['url']

    try:
        response = YOUTUBE.videos().list(
            part='snippet,contentDetails',
            id=video_id
        ).execute()

        if not response['items']:
            raise Http404(
                'The video is unavailable. It might be private or deleted.')

        video_info = response['items'][0]

        return {
            'id': video_id,
            'title': video_info['snippet']['title'],
            'thumbnail': get_thumb(video_info['snippet']['thumbnails']),
            'duration': format_duration(
                parse_duration(video_info['contentDetails']['duration']).total_seconds())
        }
    except HttpError as e:
        if e.resp.status in [403, 429]:  # Quota exceeded
            return None
        raise e


def get_video_info_from_yt_dlp(video_id):
    try:
        with YoutubeDL({
            'username': 'oauth2',
            'password': '',
        }) as ydl:
            video_info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
            return {
                'id': video_id,
                'title': video_info['title'],
                'thumbnail': video_info['thumbnail'],
                'duration': format_duration(video_info['duration'])
            }

    except DownloadError as e:
        if 'video unavailable' in e.msg.lower():
            raise Http404(
                'The video is unavailable. It might be private or deleted.')

        raise Exception(e.msg)

    except Exception as e:
        raise Exception(f'An unexpected error occurred: {str(e.msg)}')


def handle_download_task(request, video_id, format):
    task_id = f"{video_id}_{format}"
    task = celery_app.AsyncResult(task_id)

    def resp(kwargs, status=200):
        return JsonResponse(
            {
                'task_id': task.id,
                'status': task.state,
                **kwargs
            }, status=status
        )

    if task.state == 'PENDING':
        task = download.apply_async(args=[video_id, format], task_id=task_id)
        return resp({'progress': 0})

    elif task.state == 'PROGRESS':
        return resp({
            'progress': min(task.info.get('percent', 0), 95) if task.info else 0
        })

    elif task.state == 'SUCCESS':
        result = task.get()

        if 'error' in result:
            return resp({'error': result['error']}, status=500)

        return resp({
            'progress': 100,
            'file_path': request.build_absolute_uri(
                os.path.join('/media/', result['file_path'])
            )
        })

    elif task.state == 'RETRY':
        return resp({'progress': 0})

    elif task.state == 'FAILURE':
        return resp({'error': str(task.result)}, status=500)

    else:
        return resp({'error': f'Unexpected task state: {task.state}'}, status=500)
