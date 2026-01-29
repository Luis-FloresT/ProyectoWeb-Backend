from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView # <--- 1. IMPORTAR ESTO

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('fiesta.urls')),
    
    # 2. AGREGAR ESTA LÍNEA (Redirección al Frontend en producción):
    # path('', RedirectView.as_view(url='https://proyectoweb-fronted.onrender.com/')), 
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

