from django.conf.urls import patterns, include, url

urlpatterns = patterns('relationship.views',
    url(r'^$', 'relationships', name='relationships'),
)