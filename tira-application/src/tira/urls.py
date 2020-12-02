from django.urls import path

from . import views

app_name = 'tira'
urlpatterns = [
    path('', views.index, name='index'),
    path('task', views.task_list, name='task'),
    path('tasks', views.task_list, name='task'),
    path('task/<str:task_id>', views.task_detail, name='task-detail'),
    path('dataset', views.dataset_list, name='dataset'),
    path('dataset/<str:dataset_id>', views.dataset_detail, name='dataset-detail'),
    path('software/<str:user_id>', views.software_detail, name='software-detail'),
]