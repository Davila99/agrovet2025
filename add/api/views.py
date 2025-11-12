from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ..models import Add, Category, Follow
from .serializers import AddSerializer, CategorySerializer, FollowSerializer
from .permissions import IsPublisherOrReadOnly


class AddViewSet(viewsets.ModelViewSet):
    queryset = Add.objects.all().select_related("publisher", "category").prefetch_related("secondary_images")
    serializer_class = AddSerializer
    permission_classes = [IsPublisherOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'condition', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'price']

    def perform_create(self, serializer):
        serializer.save(publisher=self.request.user)

    @action(detail=False, methods=["get"])
    def my_adds(self, request):
        adds = Add.objects.filter(publisher=request.user)
        return Response(self.get_serializer(adds, many=True).data)

    @action(detail=False, methods=["get"])
    def following_adds(self, request):
        followed_users = request.user.following.values_list("following_id", flat=True)
        adds = Add.objects.filter(publisher_id__in=followed_users)
        return Response(self.get_serializer(adds, many=True).data)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        # simple nearby implementation: ?lat=X&lon=Y&radius_km=5
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except Exception:
            return Response({'detail': 'lat and lon are required params'}, status=400)
        radius_km = float(request.query_params.get('radius_km', 5))
        # naive bounding box filter for performance; accurate geospatial queries require PostGIS
        km_per_deg = 111
        delta = radius_km / km_per_deg
        adds = Add.objects.filter(latitude__gte=lat-delta, latitude__lte=lat+delta, longitude__gte=lon-delta, longitude__lte=lon+delta, status='active')
        return Response(self.get_serializer(adds, many=True).data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class FollowViewSet(viewsets.ModelViewSet):
    queryset = Follow.objects.all()
    permission_classes = [IsPublisherOrReadOnly]
    serializer_class = FollowSerializer

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                following_id = request.data.get('following') or request.data.get('following_id')
                if not following_id:
                    return Response({'detail': 'following or following_id required'}, status=400)
                if int(following_id) == request.user.pk:
                    return Response({'detail': 'No puedes seguirte a ti mismo.'}, status=400)
                follow, created = Follow.objects.get_or_create(
                    follower=request.user,
                    following_id=following_id
                )
                if not created:
                    return Response({'detail': 'Ya sigues a este usuario.'}, status=400)
                return Response(self.get_serializer(follow).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            follow = self.get_object()
            if follow.follower != request.user:
                return Response({'detail': 'No tienes permiso para eliminar este seguimiento.'}, status=403)
            follow.delete()
            return Response({'detail': 'Has dejado de seguir a este usuario.'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)
