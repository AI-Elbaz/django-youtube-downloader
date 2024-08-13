import os
import re
import json
from urllib.parse import quote

from django.contrib import messages
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from django.conf import settings


from .models import Video
from .forms import URLForm
from .utils import (
    extract_video_id,
    get_random_sample,
    get_video_info_from_api,
    get_video_info_from_yt_dlp,
    handle_download_task,
    parse_duration_to_iso8601
)


@require_http_methods(["GET", "POST"])
@ratelimit(key='ip', method=['POST'], rate='1/s')
@ratelimit(key='ip', method=['POST'], rate='5/m')
def index(request):
    if request.method == 'POST':
        form = URLForm(request.POST)
        if form.is_valid():
            youtube_url = form.cleaned_data['youtube_url']
            video_id = extract_video_id(youtube_url)

            if video_id:
                return redirect(f'/download/{video_id}', permanent=True)

        messages.error(request, 'Please provide a valid URL')
        return redirect('/')

    form = URLForm()
    random_sample = get_random_sample()
    return render(request, 'index.html', {'form': form, 'sample': random_sample})


@require_http_methods(["GET"])
@ratelimit(key='ip', rate='1/s')
@ratelimit(key='ip', rate='20/m')
def download(request, video_id: str):
    try:
        video = Video.objects.get(id=video_id)

    except Video.DoesNotExist:
        try:
            video_info = get_video_info_from_api(video_id)

            if video_info is None:
                video_info = get_video_info_from_yt_dlp(video_id)

            video = Video(**video_info)
            video.save()

        except Http404 as e:
            raise Http404(str(e))

        except Exception as e:
            messages.error(request, str(e))
            return redirect('/')

    context = {
        'video': video,
        'form': URLForm(),
        'domain': settings.DOMAIN,
        'sample': get_random_sample(size=6, exclude_video_id=video.id),
        'keywords': video.title.replace(" ", ", "),
        'iso_duration': parse_duration_to_iso8601(video.duration)
    }
    return render(request, 'download.html', context=context)


@require_http_methods(["POST"])
@ratelimit(key='ip', rate='2/s')
@ratelimit(key='ip', rate='30/m')
def handle_download(request):
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        extension = data.get('extension')

        if not video_id or not extension:
            raise ValueError(
                "Missing required parameters 'video_id' or 'extension'")

        if not re.match(r'([a-zA-Z0-9_-]{11})', video_id) or not re.match(r'(mp3|mp4)', extension):
            raise ValueError("Invalid 'video id' or 'extension'")

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    get_object_or_404(Video, id=video_id)
    return handle_download_task(
        request,
        video_id=video_id,
        format=extension
    )


def serve_media_file(request, video_id, extension):
    video = get_object_or_404(Video, id=video_id)

    filepath = os.path.join(settings.MEDIA_ROOT, f"{video_id}.{extension}")
    if not os.path.exists(filepath):
        raise Http404("File does not exist")

    # For nginx
    # def rem(header):
    #     try:
    #         del response[header]
    #     except:
    #         pass

    # response = HttpResponse()
    # response['X-Accel-Redirect'] = f"/downloads/{video_id}.{extension}"
    # response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(video.title)}.{extension}"

    # rem('Content-Type')
    # rem('Accept-Ranges')
    # rem('Set-Cookie')
    # rem('Cache-Control')
    # rem('Expires')

    # return response

    response = FileResponse(open(filepath, 'rb'))
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(video.title)}.{extension}"
    return response


def privacy(request):
    return render(request, 'privacy.html', {'form': URLForm()})


def dmca(request):
    return render(request, 'dmca.html', {'form': URLForm()})
