from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/cmsroles/', include('cmsroles.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('cms.urls')),
)
