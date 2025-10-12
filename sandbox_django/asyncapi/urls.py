from django.urls import include, path

urlpatterns = [path("", include("chanx.channels.urls"))]
