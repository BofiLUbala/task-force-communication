from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import ExpoPushTokenSerializer, TaskForceTokenObtainPairSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    """Login for both agents and hierarchy — role is embedded in the JWT."""
    serializer_class = TaskForceTokenObtainPairSerializer


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user


class RegisterPushTokenView(APIView):
    """Field agents register their Expo push token here after login."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = ExpoPushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.expo_push_token = serializer.validated_data['expo_push_token']
        request.user.save(update_fields=['expo_push_token'])
        return Response(status=status.HTTP_204_NO_CONTENT)
