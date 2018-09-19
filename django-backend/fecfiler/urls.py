from django.conf.urls import url, include
from django.contrib import admin
from rest_framework_nested import routers
from .authentication.views import AccountViewSet, LoginView, LogoutView
from .posts.views import AccountPostsViewSet, PostViewSet
from .views import IndexView
from django.views.decorators.csrf import csrf_exempt
from rest_framework_swagger.views import get_swagger_view
schema_view = get_swagger_view(title='FEC-Filer API')

router = routers.SimpleRouter()
router.register(r'accounts', AccountViewSet)
router.register(r'posts', PostViewSet)

accounts_router = routers.NestedSimpleRouter(
    router, r'accounts', lookup='account'
)
accounts_router.register(r'posts', AccountPostsViewSet)

urlpatterns = (
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^admin$', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/v1/', include(router.urls)),
    url(r'^api/v1/', include(accounts_router.urls)),
    url(r'^api/v1/', include('fecfiler.forms.urls')),
    
    url(r'^api/v1/auth/login$', csrf_exempt(LoginView.as_view()), name='login'),
    url(r'^api/v1/auth/logout/$', LogoutView.as_view(), name='logout'),
    #url(r'^api/docs/', include('rest_framework_swagger.urls')),
    url(r'^api/docs/', schema_view),
    
    #url('^.*$', IndexView.as_view(), name='index'),
)