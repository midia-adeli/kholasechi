from django.urls import path
from .views import home, PDFSummaryView

urlpatterns = [
    path('', home, name='home'),
    path('api/pdf-summary/', PDFSummaryView.as_view(), name='pdf-summary'),
]
