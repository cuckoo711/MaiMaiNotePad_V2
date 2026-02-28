"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.views.static import serve
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from application import dispatch
from application import settings
from application.sse_views import sse_view
from mainotebook.system.views.dictionary import InitDictionaryViewSet
from mainotebook.system.views.login import (
    LoginView,
    CaptchaView,
    ApiLogin,
    LogoutView,
    LoginTokenView
)
from mainotebook.system.views.register import RegisterView, VerifyEmailView, ResendVerificationView
from mainotebook.system.views.system_config import InitSettingsViewSet
from mainotebook.utils.swagger import CustomOpenAPISchemaGenerator
from mainotebook.content.views import UserExtensionViewSet

# 头像访问视图（公开访问）
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.shortcuts import redirect
from django.http import Http404
from mainotebook.system.models import Users
from mainotebook.utils.json_response import ErrorResponse
from rest_framework import status as http_status

@api_view(['GET'])
@permission_classes([AllowAny])
def user_avatar_view(request, pk):
    """获取用户头像（公开访问）
    
    Args:
        request: HTTP 请求对象
        pk: 用户ID
        
    Returns:
        Response: 重定向到头像文件或返回404
    """
    try:
        user = Users.objects.get(pk=pk)
        if user.avatar:
            # 如果是完整URL（http/https开头），直接重定向
            if user.avatar.startswith('http'):
                return redirect(user.avatar)
            # 如果已经是完整路径（/media/开头），直接重定向
            if user.avatar.startswith('/media/'):
                return redirect(user.avatar)
            # 如果是相对路径，拼接MEDIA_URL
            avatar_url = f"{settings.MEDIA_URL}{user.avatar}".replace('//', '/')
            return redirect(avatar_url)
        else:
            # 用户没有头像
            raise Http404("User has no avatar")
    except (Users.DoesNotExist, Http404):
        raise Http404("User not found")
    except Exception as e:
        return ErrorResponse(
            msg=f"获取头像失败: {str(e)}",
            status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# =========== 初始化系统配置 =================
dispatch.init_system_config()
dispatch.init_dictionary()
# =========== 初始化系统配置 =================

permission_classes = [permissions.AllowAny, ] if settings.DEBUG else [permissions.IsAuthenticated, ]
schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=permission_classes,
    generator_class=CustomOpenAPISchemaGenerator,
)
# 前端页面映射
from django.http import Http404, HttpResponse
from django.shortcuts import render
import mimetypes
import os


def web_view(request):
    return render(request, 'web/index.html')


def serve_web_files(request, filename):
    # 设定文件路径
    filepath = os.path.join(settings.BASE_DIR, 'templates', 'web', filename)

    # 检查文件是否存在
    if not os.path.exists(filepath):
        raise Http404("File does not exist")

    # 根据文件扩展名，确定 MIME 类型
    mime_type, _ = mimetypes.guess_type(filepath)

    # 打开文件并读取内容
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type=mime_type)
        return response


urlpatterns = (
        [
            re_path(
                r"^swagger(?P<format>\.json|\.yaml)$",
                schema_view.without_ui(cache_timeout=0),
                name="schema-json",
            ),
            path(
                "",
                schema_view.with_ui("swagger", cache_timeout=0),
                name="schema-swagger-ui",
            ),
            path(
                r"redoc/",
                schema_view.with_ui("redoc", cache_timeout=0),
                name="schema-redoc",
            ),
            path("api/system/", include("mainotebook.system.urls")),
            path("api/content/", include("mainotebook.content.urls")),
            # 邮箱注册相关路由（公开接口，无需认证）
            path("api/register/", RegisterView.as_view(), name="register"),
            path("api/verify-email/", VerifyEmailView.as_view(), name="verify_email"),
            path("api/resend-verification/", ResendVerificationView.as_view(), name="resend_verification"),
            path("api/login/", LoginView.as_view(), name="token_obtain_pair"),
            path("api/logout/", LogoutView.as_view(), name="token_obtain_pair"),
            path("api/users/<str:pk>/avatar/", user_avatar_view, name='user-avatar'),
            path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
            re_path(
                r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")
            ),
            path("api/captcha/", CaptchaView.as_view()),
            path("api/init/dictionary/", InitDictionaryViewSet.as_view()),
            path("api/init/settings/", InitSettingsViewSet.as_view()),
            path("apiLogin/", ApiLogin.as_view()),

            # 仅用于开发，上线需关闭
            path("api/token/", LoginTokenView.as_view()),
            # 前端页面映射
            path('web/', web_view, name='web_view'),
            path('web/<path:filename>', serve_web_files, name='serve_web_files'),
            # sse
            path('sse/', sse_view, name='sse'),
            re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        ]
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        + static(settings.STATIC_URL, document_root=settings.STATIC_URL)
        + [re_path(ele.get('re_path'), include(ele.get('include'))) for ele in settings.PLUGINS_URL_PATTERNS]
)
