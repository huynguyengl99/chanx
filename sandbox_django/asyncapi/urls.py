from django.urls import include, path

urlpatterns = [path("", include("chanx.ext.channels.urls"))]
