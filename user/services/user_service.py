"""
User Service
"""
from typing import Optional
from django.db import transaction
from django.contrib.auth.hashers import make_password
from common.services.base_service import BaseService
from common.exceptions import ValidationException, DuplicateException, ResourceNotFoundException
from user.models import User
from user.repositories.user_repository import UserRepository


class UserService(BaseService[User]):
    """用户 Service"""

    def __init__(self):
        super().__init__(UserRepository())

    @transaction.atomic
    def create_user(self, data: dict, creator=None) -> User:
        """创建用户"""
        if not data.get('username'):
            raise ValidationException("用户名不能为空")

        if not data.get('password'):
            raise ValidationException("密码不能为空")

        if not data.get('real_name'):
            raise ValidationException("真实姓名不能为空")

        if self.repository.exists_by_username(data['username']):
            raise DuplicateException(f"用户名 '{data['username']}' 已存在")

        if data.get('email') and self.repository.exists_by_email(data['email']):
            raise DuplicateException(f"邮箱 '{data['email']}' 已存在")

        user_data = {
            'username': data['username'],
            'password': make_password(data['password']),
            'real_name': data['real_name'],
            'email': data.get('email', ''),
            'phone_number': data.get('phone_number', ''),
            'is_active': data.get('is_active', True),
            'is_system_admin': data.get('is_system_admin', False),
        }

        if 'avatar' in data:
            user_data['avatar'] = data['avatar']

        return self.repository.create(user_data, creator=creator)

    @transaction.atomic
    def update_user(self, user_id: int, data: dict, updater=None) -> User:
        """更新用户"""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("用户不存在")

        if 'username' in data and data['username'] != user.username:
            if self.repository.exists_by_username(data['username'], exclude_id=user_id):
                raise DuplicateException(f"用户名 '{data['username']}' 已存在")

        if 'email' in data and data['email'] != user.email:
            if self.repository.exists_by_email(data['email'], exclude_id=user_id):
                raise DuplicateException(f"邮箱 '{data['email']}' 已存在")

        if 'password' in data:
            data['password'] = make_password(data['password'])

        return self.repository.update(user_id, data)

    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.repository.get_by_username(username)

    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.repository.get_by_email(email)

    def get_active_users(self):
        """获取所有活跃用户"""
        return self.repository.get_active_users()

    def get_system_admins(self):
        """获取所有系统管理员"""
        return self.repository.get_system_admins()

    def count_by_status(self, is_active: Optional[bool] = None) -> int:
        """统计用户数量"""
        return self.repository.count_by_status(is_active)

    @transaction.atomic
    def activate_user(self, user_id: int) -> User:
        """激活用户"""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("用户不存在")

        return self.repository.update(user_id, {'is_active': True})

    @transaction.atomic
    def deactivate_user(self, user_id: int) -> User:
        """停用用户"""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("用户不存在")

        return self.repository.update(user_id, {'is_active': False})
