from django.urls import path
from .views import (
    RAGQueryView, RAGAutoEmbedView, RDFQueryView, RDFAnalysisView
)

urlpatterns = [
    path('query/', RAGQueryView.as_view(), name='rag-query'),
    path('auto-embed/', RAGAutoEmbedView.as_view(), name='rag-auto-embed'),
    path('rdf-query/', RDFQueryView.as_view(), name='rdf-query'),
    path('rdf-analysis/', RDFAnalysisView.as_view(), name='rdf-analysis'),
]
