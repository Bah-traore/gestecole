from django.urls import path
from . import views

app_name = "core_admin"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('tenants/', views.tenants_list, name='tenants_list'),
    path('tenants/create/', views.tenant_create, name='tenant_create'),
    path('tenants/<int:tenant_id>/edit/', views.tenant_edit, name='tenant_edit'),
    path('tenants/<int:tenant_id>/delete/', views.tenant_delete, name='tenant_delete'),
]
