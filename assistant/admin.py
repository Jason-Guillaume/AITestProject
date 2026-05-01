"""
Django Admin 配置 - UI 元素库管理
"""
from django.contrib import admin
from assistant.ui_element_models import (
    UIModule,
    UIPage,
    UIPageElement,
    UITestCase,
    UIActionStep
)


@admin.register(UIModule)
class UIModuleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'project', 'parent', 'order', 'create_time']
    list_filter = ['project', 'create_time']
    search_fields = ['name', 'description']
    ordering = ['project', 'order', 'id']


@admin.register(UIPage)
class UIPageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'module', 'url', 'order', 'create_time']
    list_filter = ['module', 'create_time']
    search_fields = ['name', 'url', 'description']
    ordering = ['module', 'order', 'id']


@admin.register(UIPageElement)
class UIPageElementAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'page', 'locator_type', 'locator_value', 'order', 'create_time']
    list_filter = ['page', 'locator_type', 'create_time']
    search_fields = ['name', 'locator_value', 'description']
    ordering = ['page', 'order', 'id']


@admin.register(UITestCase)
class UITestCaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'module', 'priority', 'order', 'create_time']
    list_filter = ['module', 'priority', 'create_time']
    search_fields = ['name', 'preconditions', 'expected_result']
    ordering = ['module', 'order', 'id']


@admin.register(UIActionStep)
class UIActionStepAdmin(admin.ModelAdmin):
    list_display = ['id', 'test_case', 'sequence', 'action_type', 'element', 'create_time']
    list_filter = ['test_case', 'action_type', 'create_time']
    search_fields = ['description', 'test_data']
    ordering = ['test_case', 'sequence']
