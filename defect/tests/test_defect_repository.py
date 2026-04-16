"""
Defect Repository 单元测试
"""
import pytest
from django.contrib.auth import get_user_model
from defect.repositories.defect_repository import DefectRepository
from defect.models import TestDefect

User = get_user_model()


@pytest.mark.django_db
class TestDefectRepository:
    """缺陷 Repository 测试"""

    def test_get_by_id(self, defect):
        """测试根据 ID 获取缺陷"""
        repo = DefectRepository()
        result = repo.get_by_id(defect.id)

        assert result is not None
        assert result.id == defect.id
        assert result.defect_no == 'BUG-001'

    def test_get_by_id_not_found(self):
        """测试获取不存在的缺陷"""
        repo = DefectRepository()
        result = repo.get_by_id(99999)

        assert result is None

    def test_get_all(self, user, handler):
        """测试获取所有缺陷"""
        repo = DefectRepository()

        # 创建测试数据
        TestDefect.objects.create(
            defect_no='BUG-001',
            defect_name='缺陷1',
            status=1,
            severity=2,
            priority=2,
            handler=handler,
            creator=user
        )
        TestDefect.objects.create(
            defect_no='BUG-002',
            defect_name='缺陷2',
            status=2,
            severity=1,
            priority=1,
            handler=handler,
            creator=user
        )

        # 查询所有缺陷
        defects = repo.get_all()
        assert defects.count() == 2

        # 按状态过滤
        defects = repo.get_all(filters={'status': 1})
        assert defects.count() == 1
        assert defects.first().status == 1

    def test_get_all_with_search(self, user, handler):
        """测试搜索缺陷"""
        repo = DefectRepository()

        TestDefect.objects.create(
            defect_no='BUG-001',
            defect_name='登录失败',
            defect_content='用户无法登录',
            handler=handler,
            creator=user
        )
        TestDefect.objects.create(
            defect_no='BUG-002',
            defect_name='注册失败',
            defect_content='用户无法注册',
            handler=handler,
            creator=user
        )

        # 搜索关键词
        defects = repo.get_all(filters={'search': '登录'})
        assert defects.count() == 1
        assert defects.first().defect_name == '登录失败'

    def test_get_by_handler(self, user, handler):
        """测试获取处理人的缺陷"""
        repo = DefectRepository()

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

        defects = repo.get_by_handler(handler.id)
        assert defects.count() == 2

    def test_exists_by_no(self, defect):
        """测试检查缺陷编号是否存在"""
        repo = DefectRepository()

        # 存在的编号
        exists = repo.exists_by_no('BUG-001')
        assert exists is True

        # 不存在的编号
        exists = repo.exists_by_no('BUG-999')
        assert exists is False

        # 排除当前缺陷
        exists = repo.exists_by_no('BUG-001', exclude_id=defect.id)
        assert exists is False

    def test_create(self, user, handler):
        """测试创建缺陷"""
        repo = DefectRepository()

        data = {
            'defect_no': 'BUG-NEW',
            'defect_name': '新缺陷',
            'defect_content': '新缺陷内容',
            'severity': 2,
            'priority': 2,
            'status': 1,
            'handler': handler
        }

        defect = repo.create(data, creator=user)

        assert defect.id is not None
        assert defect.defect_no == 'BUG-NEW'
        assert defect.creator == user

    def test_update(self, defect):
        """测试更新缺陷"""
        repo = DefectRepository()

        data = {
            'defect_name': '更新后的名称',
            'status': 2
        }

        updated = repo.update(defect.id, data)

        assert updated is not None
        assert updated.defect_name == '更新后的名称'
        assert updated.status == 2

    def test_delete_soft(self, defect):
        """测试软删除缺陷"""
        repo = DefectRepository()

        result = repo.delete(defect.id, soft=True)

        assert result is True

        # 验证软删除
        defect.refresh_from_db()
        assert defect.is_deleted is True

    def test_count_by_status(self, user, handler):
        """测试统计缺陷数"""
        repo = DefectRepository()

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

        # 统计所有缺陷
        count = repo.count_by_status()
        assert count == 2

        # 按状态统计
        count = repo.count_by_status(status=1)
        assert count == 1

    def test_count_by_severity(self, user, handler):
        """测试按严重程度统计缺陷数"""
        repo = DefectRepository()

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

        count = repo.count_by_severity(severity=1)
        assert count == 2
