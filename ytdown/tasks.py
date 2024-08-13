import os
import gc
import json
import logging
import subprocess
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from celery import shared_task
from django_celery_results.models import TaskResult
from celery_progress.backend import ProgressRecorder

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def download(self, video_id, format):
    self.update_state(state='PROGRESS', meta={'progress': 0})
    progress_recorder = ProgressRecorder(self)

    def progress_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes', 1)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            progress_recorder.set_progress(downloaded_bytes, total_bytes)

    yt_dlp_options = {
        'mp3': {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(id)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'progress_hooks': [progress_hook],
            'username': 'oauth2',
            'password': '',
        },
        'mp4': {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook],
            'username': 'oauth2',
            'password': '',
        }
    }

    try:
        with YoutubeDL(yt_dlp_options[format]) as ydl:
            result = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=True
            )
            file_path = ydl.prepare_filename(result)
            del result

        file_path = os.path.splitext(file_path)[0] + f'.{format}'
        return {'file_path': os.path.basename(file_path)}

    except DownloadError as e:
        if 'video unavailable' in (e.msg or '').lower():
            return {'error': 'The video is unavailable. It might be private or deleted.'}

        elif 'truncated_id' in (e.msg or '').lower():
            return {'error': 'The video is unavailable'}

        raise self.retry(exc=e)

    except Exception as e:
        raise self.retry(exc=e)

    finally:
        gc.collect()


@shared_task
def cleanup_old_tasks():
    cutoff_time = timezone.now() - timedelta(days=1)
    old_tasks = TaskResult.objects.filter(
        date_done__lt=cutoff_time,
        task_id__regex=r'(_mp3|_mp4)$',
        status__in=['FAILURE', 'SUCCESS'],
    )

    for task in old_tasks:
        task_info = json.loads(task.result)

        if task_info and 'file_path' in task_info:
            file_path = os.path.join(
                settings.MEDIA_ROOT, task_info['file_path']
            )

            if os.path.exists(file_path):
                os.remove(file_path)

        task.delete()
        logger.info(f"DELETED: {task.task_id}")

    return {
        'deleted_videos': [t.task_id for t in old_tasks]
    }


@shared_task
def update_yt_dlp():
    try:
        result = subprocess.run(
            ['pip', 'install', '-U', 'yt-dlp'], capture_output=True, text=True)
        logger.info(f"Output: {result.stdout}")
        logger.info(f"Error: {result.stderr}")
        if result.returncode == 0:
            logger.info("yt-dlp updated successfully")
        else:
            logger.error(
                f"Failed to update yt-dlp. Return code: {result.returncode}")
    except Exception as e:
        logger.error(f"Exception occurred while updating yt-dlp: {e}")
