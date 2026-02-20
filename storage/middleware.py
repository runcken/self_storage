from .models import AdTransition
from django.utils import timezone
import hashlib

class AdTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utm_source = request.GET.get('utm_source')
        
        if utm_source:
            if not request.session.session_key:
                request.session.create()
            
            session_key = request.session.session_key

            recent_transition = AdTransition.objects.filter(
                session_key=session_key,
                created_at__gt=timezone.now() - timezone.timedelta(minutes=30)
            ).exists()

            if not recent_transition:
                source_map = {
                    'yandex': 'yandex',
                    'google': 'google',
                    'vk': 'vk',
                    'telegram': 'telegram',
                }
                source_slug = source_map.get(utm_source.lower(), 'other')

                AdTransition.objects.create(
                    session_key=session_key,
                    source=source_slug,
                    medium=request.GET.get('utm_medium', ''),
                    campaign=request.GET.get('utm_campaign', ''),
                    term=request.GET.get('utm_term', ''),
                    content=request.GET.get('utm_content', ''),
                    landing_page=request.build_absolute_uri(),
                )

        response = self.get_response(request)
        return response
        