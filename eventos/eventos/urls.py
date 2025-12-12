from django.contrib import admin
from django.urls import path, include
from fiesta.views import home  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('fiesta.urls')),  # <- Esto es CRUCIAL
      path('', home, name='home'), 
]
