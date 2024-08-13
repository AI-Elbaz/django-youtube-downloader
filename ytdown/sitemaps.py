from django.contrib.sitemaps import Sitemap
from .models import Video


class VideoSitemap(Sitemap):
    changefreq = 'weekly'
    protocol = 'https'
    priority = 0.9
    limit = 20_000

    def items(self):
        return Video.objects.all().order_by('-id')
