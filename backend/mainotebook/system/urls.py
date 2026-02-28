from django.urls import path
from rest_framework import routers

from mainotebook.system.views.api_white_list import ApiWhiteListViewSet
from mainotebook.system.views.area import AreaViewSet
from mainotebook.system.views.clause import PrivacyView, TermsServiceView
from mainotebook.system.views.dept import DeptViewSet
from mainotebook.system.views.dictionary import DictionaryViewSet
from mainotebook.system.views.file_list import FileViewSet
from mainotebook.system.views.login_log import LoginLogViewSet
from mainotebook.system.views.menu import MenuViewSet
from mainotebook.system.views.menu_button import MenuButtonViewSet
from mainotebook.system.views.message_center import MessageCenterViewSet
from mainotebook.system.views.operation_log import OperationLogViewSet
from mainotebook.system.views.role import RoleViewSet
from mainotebook.system.views.role_menu import RoleMenuPermissionViewSet
from mainotebook.system.views.role_menu_button_permission import RoleMenuButtonPermissionViewSet
from mainotebook.system.views.system_config import SystemConfigViewSet
from mainotebook.system.views.user import UserViewSet
from mainotebook.system.views.menu_field import MenuFieldViewSet
from mainotebook.system.views.download_center import DownloadCenterViewSet

system_url = routers.SimpleRouter()
system_url.register(r'menu', MenuViewSet)
system_url.register(r'menu_button', MenuButtonViewSet)
system_url.register(r'role', RoleViewSet)
system_url.register(r'dept', DeptViewSet)
system_url.register(r'user', UserViewSet)
system_url.register(r'operation_log', OperationLogViewSet)
system_url.register(r'dictionary', DictionaryViewSet)
system_url.register(r'area', AreaViewSet)
system_url.register(r'file', FileViewSet)
system_url.register(r'api_white_list', ApiWhiteListViewSet)
system_url.register(r'system_config', SystemConfigViewSet)
system_url.register(r'message_center', MessageCenterViewSet)
system_url.register(r'role_menu_button_permission', RoleMenuButtonPermissionViewSet)
system_url.register(r'role_menu_permission', RoleMenuPermissionViewSet)
system_url.register(r'column', MenuFieldViewSet)
system_url.register(r'login_log', LoginLogViewSet)
system_url.register(r'download_center', DownloadCenterViewSet)


urlpatterns = [
    path('user/export/', UserViewSet.as_view({'post': 'export_data', })),
    path('user/import/', UserViewSet.as_view({'get': 'import_data', 'post': 'import_data'})),
    path('system_config/save_content/', SystemConfigViewSet.as_view({'put': 'save_content'})),
    path('system_config/get_association_table/', SystemConfigViewSet.as_view({'get': 'get_association_table'})),
    path('system_config/get_table_data/<str:pk>/', SystemConfigViewSet.as_view({'get': 'get_table_data'})),
    path('system_config/get_relation_info/', SystemConfigViewSet.as_view({'get': 'get_relation_info'})),
    # path('login_log/', LoginLogViewSet.as_view({'get': 'list'})),
    # path('login_log/<str:pk>/', LoginLogViewSet.as_view({'get': 'retrieve'})),
    # path('dept_lazy_tree/', DeptViewSet.as_view({'get': 'dept_lazy_tree'})),
    path('clause/privacy.html', PrivacyView.as_view()),
    path('clause/terms_service.html', TermsServiceView.as_view()),
]
urlpatterns += system_url.urls
