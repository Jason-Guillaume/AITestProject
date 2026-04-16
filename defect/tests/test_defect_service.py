"""
Defect Service 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from defect.services.defect_service import DefectService
from defect.models import TestDefect
from common.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    DuplicateException
)

User = get_user_model()


@pytest.mark.django_db
class TestDefectService:
    """缺陷 Service 测试"""

    def test_create_defect_success(self, user, handler):
        """测试成功创建缺陷"""
        service = DefectService()

        data = {
            'defect_no': 'BUG-NEW',
            'defect_name': '新缺陷',
            'defect_content': '缺陷内容',
            'severity': 2,
            'priority': 2,
            'status': 1,
            'handler_id': handler.id
        }

        defect = service.create_defect(data, user)

        assert defect.id is not None
        assert defect.defect_no == 'BUG-NEW'
        assert defect.creator == user

    def test_create_defect_missing_no(self, user, handler):
        """测试创建缺陷时缺少编号"""
        service = DefectService()

        data = {
            'defect_name': '新缺陷',
            'handler_id': handler.id
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_defect(data, user)

        assert "缺陷编号不能为空" in str(exc_info.value)

    def test_create_defect_missing_name(self, user, handler):
        """测试创建缺陷时缺少标题"""
        service = DefectService()

        data = {
            'defect_no': 'BUG-NEW',
            'handler_id': handler.id
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_defect(data, user)

        assert "缺陷标题不能为空" in str(exc_info.value)

    def test_create_defect_missing_handler(self, user):
        """测试创建缺陷时缺少处理人"""
        service = DefectService()

        data = {
            'defect_no': 'BUG-NEW',
            'defect_name': '新缺陷'
        }

        with pytest.raises(ValidationException) as exc_info:
            service.create_defect(data, user)

        assert "处理人不能为空" in str(exc_info.value)

    def test_create_defect_duplicate_no(self, defect, user, handler):
        """测试创建缺陷时编号重复"""
        service = DefectService()

        data = {
            'defect_no': defect.defect_no,
            'defect_name': '新缺陷',
            'handler_id': handler.id
        }

        with pytest.raises(DuplicateException) as exc_info:
            service.create_defect(data, user)

        assert "已存在" in str(exc_info.value)

    def test_update_defect_success(self, defect, user):
        """测试成功更新缺陷"""
        service = DefectService()

        data = {
            'defect_name': '更新后的名称',
            'status': 2
        }

        updated = service.update_defect(defect.id, data, user)

        assert updated.defect_name == '更新后的名称'
        assert updated.status == 2

    def test_update_defect_not_found(self, user):
        """测试更新不存在的缺陷"""
        service = DefectService()

        data = {'defect_name': '新名称'}

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.update_defect(99999, data, user)

        assert "缺陷不存在" in str(exc_info.value)

    def test_update_defect_duplicate_no(self, user, handler, defect):
        """测试更新缺陷时编号重复"""
        service = DefectService()

        # 创建另一个缺陷
        another_defect = TestDefect.objects.create(
            defect_no='BUG-002',
            defect_name='另一个缺陷',
            handler=handler,
            creator=user
        )

        data = {'defect_no': defect.defect_no}

        with pytest.raises(DuplicateException) as exc_info:
            service.update_defect(another_defect.id, data, user)

        assert "已存在" in str(exc_info.value)

    def test_delete_defect(self, defect):
        """测试删除缺陷"""
        service = DefectService()

        result = service.delete(defect.id)

        assert result is True

        defect.refresh_from_db()
        assert defect.is_deleted is True

    def test_get_all(self, user, handler):
        """测试获取所有缺陷"""
        service = DefectService()

        TestDefect.objects.create(
            defect_no='BUG-001',
            defect_name='缺陷1',
            handler=handler,
            creator=user
        )
        TestDefect.objects.create(
            defect_no='BUG-002',
            defect_name='缺陷2',
            handler=handler,
            creator=user
        )

        defects = service.get_all()

        assert len(defects) == 2

    def test_get_by_handler(self, user, handler):
        """测试获取处理人的缺陷"""
        service = DefectService()

        TestDefect.objects.create(
            defect_no='BUG-001',
            defect_name='缺陷1',
            handler=handler,
            creator=user
        )
        TestDefect.objects.create(
            defect_no='BUG-002',
            defect_name='缺陷2',
            handler=handler,
            creator=user
        )

        defects = service.get_by_handler(handler.id)

        assert len(defects) == 2

    def test_count_by_status(self, user, handler):
        """测试统计缺陷数"""
        service = DefectService()

        TestDefect.objects.create(
            defect_no='BUG-001',
            defect_name='缺陷1',
            status=1,
            handler=handler,
            creator=user
        )
        TestDefect.objects.create(
            defect_no='BUG-002',
            defect_name='缺陷2',
            status=2,
            handler=handler,
            creator=user
        )

        count = service.count_by_status()
        assert count == 2

        count_status = service.count_by_status(status=1)
        assert count_status == 1

    def test_count_by_severity(self, user, handler):
        """测试按严重程度统计缺陷数"""
        service = DefectService()

        TestDefect.objects.create(
            defect_no='BUG-001',
            defect_name='缺陷1',
            severity=1,
            handler=handler,
            creator=user
        )
        TestDefect.objects.create(
            defect_no='BUG-002',
            defect_name='缺陷2',
            severity=1,
            handler=handler,
            creator=user
        )

        count = service.count_by_severity(severity=1)
        assert count == 2

    def test_update_status(self, defect, user):
        """测试更新缺陷状态"""
        service = DefectService()

        updated = service.update_status(defect.id, 2, user)

        assert updated.status == 2

    def test_assign_handler(self, defect, user, handler):
        """测试分配处理人"""
        service = DefectService()

        # 创建新的处理人
        new_handler = User.objects.create_user(
            username='newhandler',
            password='testpass123',
            real_name='新处理人'
        )

        updated = service.assign_handler(defect.id, new_handler.id, user)

        assert updated.handler_id == new_handler.id
