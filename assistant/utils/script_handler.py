import os
import zipfile
import shutil
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def handle_script_upload(instance):
    """
    处理脚本上传后的操作

    Args:
        instance: UIScriptUpload模型实例

    功能:
    1. 如果是ZIP文件，解压到工作空间
    2. 验证入口点文件是否存在
    3. 更新workspace_path字段
    """
    file_path = instance.file_path.path

    # 如果是ZIP文件，需要解压
    if instance.is_zip:
        workspace_path = _extract_zip(instance, file_path)
        instance.workspace_path = workspace_path
        instance.save(update_fields=['workspace_path'])

        logger.info(f"ZIP文件已解压到: {workspace_path}")
    else:
        # 单文件，工作空间就是文件所在目录
        instance.workspace_path = os.path.dirname(file_path)
        instance.save(update_fields=['workspace_path'])

    # 验证入口点
    _validate_entry_point(instance)


def _extract_zip(instance, zip_path):
    """
    解压ZIP文件到工作空间

    Args:
        instance: UIScriptUpload实例
        zip_path: ZIP文件路径

    Returns:
        str: 解压后的工作空间路径
    """
    # 创建工作空间目录: media/workspaces/{id}/
    workspace_base = os.path.join(settings.MEDIA_ROOT, 'workspaces')
    os.makedirs(workspace_base, exist_ok=True)

    workspace_path = os.path.join(workspace_base, str(instance.id))

    # 如果目录已存在，先删除
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path)

    os.makedirs(workspace_path)

    # 解压ZIP
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(workspace_path)

        logger.info(f"ZIP解压成功: {zip_path} -> {workspace_path}")
        return workspace_path

    except zipfile.BadZipFile as e:
        logger.error(f"ZIP文件损坏: {zip_path}")
        raise ValueError(f"ZIP文件损坏: {str(e)}")

    except Exception as e:
        logger.error(f"ZIP解压失败: {str(e)}", exc_info=True)
        raise


def _validate_entry_point(instance):
    """
    验证入口点文件是否存在

    Args:
        instance: UIScriptUpload实例

    Raises:
        FileNotFoundError: 入口点文件不存在
    """
    workspace_path = instance.workspace_path
    entry_point = instance.entry_point

    # 构建完整路径
    entry_full_path = os.path.join(workspace_path, entry_point)

    if not os.path.exists(entry_full_path):
        error_msg = f"入口点文件不存在: {entry_point}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    if not entry_full_path.endswith('.py'):
        error_msg = f"入口点必须是Python文件: {entry_point}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"入口点验证通过: {entry_full_path}")


def cleanup_workspace(instance):
    """
    清理工作空间（删除脚本时调用）

    Args:
        instance: UIScriptUpload实例
    """
    if instance.workspace_path and os.path.exists(instance.workspace_path):
        try:
            # 只删除workspaces下的目录
            if 'workspaces' in instance.workspace_path:
                shutil.rmtree(instance.workspace_path)
                logger.info(f"工作空间已清理: {instance.workspace_path}")
        except Exception as e:
            logger.error(f"清理工作空间失败: {str(e)}", exc_info=True)
