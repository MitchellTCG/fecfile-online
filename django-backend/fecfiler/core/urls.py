from  django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^core/get_filed_report_types$', views.get_filed_report_types, name='get_filed_report_types'),
    url(r'^core/get_filed_form_types$', views.get_filed_form_types, name='get_filed_form_types'),
    url(r'^core/get_transaction_categories$', views.get_transaction_categories, name='get_transaction_categories'),
    url(r'^core/get_report_types$', views.get_report_types, name='get_report_types'),
]
