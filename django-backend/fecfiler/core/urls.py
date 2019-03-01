from  django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^core/get_filed_report_types$', views.get_filed_report_types, name='get_filed_report_types'),
    url(r'^core/get_filed_form_types$', views.get_filed_form_types, name='get_filed_form_types'),
    url(r'^core/get_transaction_categories$', views.get_transaction_categories, name='get_transaction_categories'),
    url(r'^core/get_report_types$', views.get_report_types, name='get_report_types'),
    url(r'^core/get_dynamic_forms_fields$', views.get_dynamic_forms_fields, name='get_dynamic_forms_fields'),
    url(r'^core/create_json_file$', views.create_json_file, name='create_json_file'),
    url(r'^core/reports$', views.reports, name='reports'),
    url(r'^core/entities$', views.entities, name='entities'),
    url(r'^core/search_entities$', views.search_entities, name='search_entities'),
    url(r'^core/get_all_transactions$', views.get_all_transactions, name='get_all_transactions'),
]