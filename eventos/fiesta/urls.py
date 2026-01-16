from django.urls import path, include

urlpatterns = [
    path('', include('fiesta.api.urls')),
]
