from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters
from .models import Event
from .serializers import EventSerializer, EventDetailSerializer

class EventFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name='event_day', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='event_day', lookup_expr='lte')
    
    class Meta:
        model = Event
        fields = ['event_day', 'event_type', 'pregnancy', 'start_date', 'end_date']

class EventViewSet(viewsets.ModelViewSet):
    """
    일정 관리 ViewSet
    
    list: 일정 목록 조회 (월별/일별 필터링 가능)
    retrieve: 일정 상세 조회
    create: 일정 생성
    update: 일정 수정
    destroy: 일정 삭제
    """
    permission_classes = [IsAuthenticated]
    filterset_class = EventFilter
    
    def get_queryset(self):
        # 사용자의 임신 정보에 해당하는 일정만 조회
        return Event.objects.filter(
            pregnancy__user=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return EventDetailSerializer
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save()