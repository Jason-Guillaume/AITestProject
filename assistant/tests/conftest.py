"""
测试配置文件
"""
import pytest
from django.contrib.auth import get_user_model
from assistant.models import KnowledgeArticle, KnowledgeDocument, GeneratedTestArtifact
from testcase.models import TestModule
from project.models import TestProject

User = get_user_model()


@pytest.fixture
def user(db):
    """创建测试用户"""
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        real_name='测试用户'
    )


@pytest.fixture
def project(db, user):
    """创建测试项目"""
    return TestProject.objects.create(
        project_name='测试项目',
        description='这是一个测试项目',
        project_status=1,
        creator=user
    )


@pytest.fixture
def module(db, user, project):
    """创建测试模块"""
    return TestModule.objects.create(
        name='测试模块',
        project=project,
        creator=user
    )


@pytest.fixture
def knowledge_article(db, user):
    """创建知识文章"""
    return KnowledgeArticle.objects.create(
        title='测试文章',
        category=KnowledgeArticle.CATEGORY_TEMPLATE,
        markdown_content='# 测试内容\n这是一篇测试文章',
        visibility_scope=KnowledgeArticle.VISIBILITY_PRIVATE,
        tags=['测试', 'demo'],
        creator=user
    )


@pytest.fixture
def knowledge_document(db, user, module, knowledge_article):
    """创建知识文档"""
    return KnowledgeDocument.objects.create(
        title='测试文档',
        file_name='test.pdf',
        document_type=KnowledgeDocument.DOC_TYPE_PDF,
        source_type=KnowledgeDocument.SOURCE_UPLOAD,
        status=KnowledgeDocument.STATUS_PENDING,
        visibility_scope=KnowledgeDocument.VISIBILITY_PRIVATE,
        module=module,
        article=knowledge_article,
        tags=['测试'],
        creator=user
    )


@pytest.fixture
def generated_artifact(db, user, project, module, knowledge_document):
    """创建生成的测试资产"""
    return GeneratedTestArtifact.objects.create(
        artifact_type=GeneratedTestArtifact.TYPE_CASE_DRAFT,
        title='测试用例草稿',
        content={'cases': [{'name': '测试用例1'}]},
        citations=[],
        model_used='gpt-4',
        project=project,
        module=module,
        source_document=knowledge_document,
        creator=user
    )
