"""
UI元素库视图 - CRUD API
"""
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from assistant.ui_element_models import (
    UIModule,
    UIPage,
    UIPageElement,
    UITestCase,
    UIActionStep
)
from assistant.ui_element_serializers import (
    UIModuleSerializer,
    UIModuleTreeSerializer,
    UIPageSerializer,
    UIPageElementSerializer,
    UITestCaseSerializer,
    UIActionStepSerializer
)


class UIModuleViewSet(viewsets.ModelViewSet):
    """UI模块管理ViewSet"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UIModuleSerializer
    queryset = UIModule.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        parent_id = self.request.query_params.get('parent_id')

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        if parent_id:
            if parent_id == 'null' or parent_id == '0':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)

        return queryset.order_by('order', 'id')

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取模块树形结构"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'error': 'project_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 只获取根模块（没有父模块的）
        root_modules = UIModule.objects.filter(
            project_id=project_id,
            parent__isnull=True
        ).order_by('order', 'id')

        serializer = UIModuleTreeSerializer(root_modules, many=True)
        return Response(serializer.data)


class UIPageViewSet(viewsets.ModelViewSet):
    """UI页面管理ViewSet"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UIPageSerializer
    queryset = UIPage.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        module_id = self.request.query_params.get('module_id')

        if module_id:
            queryset = queryset.filter(module_id=module_id)

        return queryset.order_by('order', 'id')


class UIPageElementViewSet(viewsets.ModelViewSet):
    """UI页面元素管理ViewSet"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UIPageElementSerializer
    queryset = UIPageElement.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        page_id = self.request.query_params.get('page_id')
        module_id = self.request.query_params.get('module_id')
        search = self.request.query_params.get('search')

        if page_id:
            queryset = queryset.filter(page_id=page_id)

        if module_id:
            queryset = queryset.filter(page__module_id=module_id)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(locator_value__icontains=search)
            )

        return queryset.order_by('order', 'id')

    @action(detail=False, methods=['get'])
    def by_name(self, request):
        """根据元素名称查找元素（用于AI脚本生成时查找元素）"""
        name = request.query_params.get('name')
        page_id = request.query_params.get('page_id')

        if not name:
            return Response(
                {'error': 'name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = UIPageElement.objects.filter(name__iexact=name)

        if page_id:
            queryset = queryset.filter(page_id=page_id)

        element = queryset.first()

        if element:
            serializer = self.get_serializer(element)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Element not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UITestCaseViewSet(viewsets.ModelViewSet):
    """UI测试用例管理ViewSet"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UITestCaseSerializer
    queryset = UITestCase.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        module_id = self.request.query_params.get('module_id')

        if module_id:
            queryset = queryset.filter(module_id=module_id)

        return queryset.order_by('order', 'id')


class UIActionStepViewSet(viewsets.ModelViewSet):
    """UI操作步骤管理ViewSet"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UIActionStepSerializer
    queryset = UIActionStep.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        test_case_id = self.request.query_params.get('test_case_id')

        if test_case_id:
            queryset = queryset.filter(test_case_id=test_case_id)

        return queryset.order_by('sequence')
