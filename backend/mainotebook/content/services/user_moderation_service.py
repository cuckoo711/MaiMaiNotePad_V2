"""用户禁言封禁管理服务

本模块提供用户禁言和封禁管理的核心业务逻辑，包括：
- 手动禁言/封禁操作
- 解除禁言/封禁操作
- 修改禁言/封禁时长
- 批量操作
- 权限验证

所有操作都会记录详细的操作日志，并发送通知给被操作用户。
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied

from mainotebook.system.models import Users
from mainotebook.content.models import UserMuteRecord, UserModerationLog
from mainotebook.content.utils.duration_parser import DurationParser
from mainotebook.content.services.moderation_notification_service import ModerationNotificationService

logger = logging.getLogger(__name__)


class UserModerationService:
    """用户禁言封禁服务类
    
    提供用户禁言和封禁管理的核心功能，包括权限验证、状态管理、
    日志记录和通知发送等。
    """
    
    @staticmethod
    def validate_permission(operator: Users, target_user: Users) -> bool:
        """验证操作权限
        
        权限规则：
        - 不能操作系统账号
        - 不能操作自己
        - 超级管理员可以操作所有人（包括普通管理员和普通用户）
        - 普通管理员只能操作普通用户（不能操作其他管理员）
        
        Args:
            operator: 执行操作的管理员用户对象
            target_user: 被操作的目标用户对象
            
        Returns:
            bool: 是否有权限执行操作
        """
        # 规则0：不能操作系统账号
        if target_user.is_system_account():
            logger.warning(
                "权限验证失败：用户 %s 尝试对系统账号 %s 执行操作",
                operator.username, target_user.username
            )
            return False
        
        # 规则1：不能操作自己
        if operator.id == target_user.id:
            logger.warning(
                "权限验证失败：用户 %s 尝试对自己执行操作",
                operator.username
            )
            return False
        
        # 规则2：超级管理员可以操作所有人
        if operator.is_superuser:
            logger.debug(
                "权限验证通过：超级管理员 %s 可以操作用户 %s",
                operator.username, target_user.username
            )
            return True
        
        # 规则3：普通管理员只能操作普通用户
        # 检查操作者是否为管理员，且目标用户不是管理员
        if operator.is_staff and not target_user.is_staff:
            logger.debug(
                "权限验证通过：普通管理员 %s 可以操作普通用户 %s",
                operator.username, target_user.username
            )
            return True
        
        # 其他情况：权限不足
        logger.warning(
            "权限验证失败：用户 %s (is_staff=%s, is_superuser=%s) "
            "无权操作用户 %s (is_staff=%s, is_superuser=%s)",
            operator.username, operator.is_staff, operator.is_superuser,
            target_user.username, target_user.is_staff, target_user.is_superuser
        )
        return False
    
    @staticmethod
    def mute_user(
        user_id: int,
        duration: str,
        reason: str,
        operator_id: Optional[int],
        mute_type: str = 'manual',
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """禁言用户
        
        执行用户禁言操作，包括：
        1. 参数验证
        2. 权限验证（如果是手动操作）
        3. 解析时长
        4. 更新用户状态
        5. 创建禁言记录
        6. 创建操作日志
        7. 发送通知
        
        Args:
            user_id: 被禁言用户ID
            duration: 时长字符串（如"3d"、"permanent"）
            reason: 禁言原因
            operator_id: 操作人ID（自动禁言时为None）
            mute_type: 禁言类型（manual/auto）
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent
            
        Returns:
            dict: 包含禁言结果的字典
            
        Raises:
            ValidationError: 参数验证失败
            PermissionDenied: 权限不足
            Users.DoesNotExist: 用户不存在
        """
        # 1. 参数验证
        if not reason or not reason.strip():
            raise ValidationError("禁言原因不能为空")
        
        # 2. 查询用户对象
        try:
            target_user = Users.objects.get(id=user_id)
        except Users.DoesNotExist:
            logger.error("禁言失败：用户不存在: user_id=%s", user_id)
            raise
        
        # 3. 权限验证（仅手动操作需要验证）
        if mute_type == 'manual' and operator_id is not None:
            try:
                operator = Users.objects.get(id=operator_id)
                if not UserModerationService.validate_permission(operator, target_user):
                    raise PermissionDenied(
                        f"权限不足：无法对用户 {target_user.username} 执行禁言操作"
                    )
            except Users.DoesNotExist:
                logger.error("禁言失败：操作人不存在: operator_id=%s", operator_id)
                raise ValidationError("操作人不存在")
        
        # 4. 解析时长
        try:
            hours = DurationParser.parse(duration)
            muted_until = DurationParser.to_datetime(duration)
        except ValueError as e:
            logger.error("禁言失败：时长格式无效: duration=%s, error=%s", duration, str(e))
            raise ValidationError(str(e))
        
        # 5. 使用数据库事务执行禁言操作
        try:
            with transaction.atomic():
                # 更新用户表
                target_user.is_muted = True
                target_user.muted_until = muted_until
                target_user.mute_reason = reason
                target_user.save(update_fields=['is_muted', 'muted_until', 'mute_reason'])
                
                logger.info(
                    "用户状态已更新: user_id=%s, is_muted=True, muted_until=%s",
                    user_id, muted_until
                )
                
                # 创建禁言记录
                mute_record = UserMuteRecord.objects.create(
                    user_id=user_id,
                    mute_type=mute_type,
                    muted_by_id=operator_id,
                    mute_reason=reason,
                    muted_until=muted_until,
                    is_active=True,
                    is_manually_modified=False
                )
                
                logger.info(
                    "禁言记录已创建: mute_record_id=%s, user_id=%s, mute_type=%s",
                    mute_record.id, user_id, mute_type
                )
                
                # 获取或创建AI审核员用户
                ai_reviewer, _ = Users.objects.get_or_create(
                    username='ai_reviewer',
                    defaults={
                        'name': 'AI 审核员',
                        'user_type': 2  # 系统账号
                    }
                )
                
                # 创建操作日志（手动和自动操作都记录）
                UserModerationLog.objects.create(
                    operator_id=operator_id if mute_type == 'manual' else ai_reviewer.id,
                    target_user_id=user_id,
                    operation_type='mute',
                    reason=reason,
                    duration_hours=hours,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    extra_data={'mute_type': mute_type}  # 记录禁言类型
                )
                
                logger.info(
                    "操作日志已创建: operator_id=%s, target_user_id=%s, operation_type=mute, mute_type=%s",
                    operator_id if mute_type == 'manual' else ai_reviewer.id, user_id, mute_type
                )
                
                # 发送通知
                try:
                    ModerationNotificationService.send_mute_notification(
                        user=target_user,
                        mute_record=mute_record
                    )
                except Exception as notify_error:
                    # 通知失败不影响主流程
                    logger.error(
                        "发送禁言通知失败: user_id=%s, error=%s",
                        user_id, str(notify_error)
                    )
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'mute_record_id': mute_record.id,
                    'muted_until': muted_until,
                    'mute_type': mute_type
                }
                
        except Exception as e:
            logger.exception(
                "禁言操作失败: user_id=%s, error=%s",
                user_id, str(e)
            )
            raise

    @staticmethod
    def unmute_user(
        user_id: int,
        operator_id: int,
        reason: Optional[str] = None,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """解除禁言

        执行用户解除禁言操作，包括：
        1. 权限验证
        2. 查询当前生效的禁言记录
        3. 更新用户状态
        4. 更新禁言记录
        5. 取消Celery自动解封任务（如果存在）
        6. 创建操作日志
        7. 发送通知

        Args:
            user_id: 被解除禁言的用户ID
            operator_id: 操作人ID
            reason: 解除原因（可选）
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含解除结果的字典

        Raises:
            ValidationError: 参数验证失败
            PermissionDenied: 权限不足
            Users.DoesNotExist: 用户不存在
        """
        # 1. 查询用户对象
        try:
            target_user = Users.objects.get(id=user_id)
            operator = Users.objects.get(id=operator_id)
        except Users.DoesNotExist:
            logger.error("解除禁言失败：用户不存在")
            raise

        # 2. 权限验证
        if not UserModerationService.validate_permission(operator, target_user):
            raise PermissionDenied(
                f"权限不足：无法对用户 {target_user.username} 执行解除禁言操作"
            )

        # 3. 查询当前生效的禁言记录
        mute_record = UserMuteRecord.objects.filter(
            user_id=user_id,
            is_active=True
        ).first()

        # 如果没有生效的禁言记录，返回成功（幂等性）
        if not mute_record:
            logger.info("解除禁言：用户当前未被禁言，操作已忽略: user_id=%s", user_id)
            return {
                'success': True,
                'user_id': user_id,
                'message': '用户当前未被禁言'
            }

        # 4. 使用数据库事务执行解除操作
        try:
            with transaction.atomic():
                # 更新用户表
                target_user.is_muted = False
                target_user.save(update_fields=['is_muted'])

                logger.info("用户状态已更新: user_id=%s, is_muted=False", user_id)

                # 更新禁言记录
                mute_record.is_active = False
                mute_record.unmuted_at = datetime.now()
                mute_record.unmuted_by_id = operator_id
                mute_record.unmute_reason = reason
                mute_record.save(update_fields=[
                    'is_active', 'unmuted_at', 'unmuted_by_id', 'unmute_reason'
                ])

                logger.info("禁言记录已更新: mute_record_id=%s, is_active=False", mute_record.id)

                # 取消Celery自动解封任务（如果存在）
                if mute_record.auto_unmute_task_id:
                    try:
                        from celery import current_app
                        current_app.control.revoke(mute_record.auto_unmute_task_id, terminate=True)
                        logger.info(
                            "已取消自动解封任务: task_id=%s",
                            mute_record.auto_unmute_task_id
                        )
                    except Exception as celery_error:
                        # Celery任务取消失败不影响主流程
                        logger.warning(
                            "取消自动解封任务失败: task_id=%s, error=%s",
                            mute_record.auto_unmute_task_id, str(celery_error)
                        )

                # 创建操作日志
                UserModerationLog.objects.create(
                    operator_id=operator_id,
                    target_user_id=user_id,
                    operation_type='unmute',
                    reason=reason or '手动解除禁言',
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                logger.info(
                    "操作日志已创建: operator_id=%s, target_user_id=%s, operation_type=unmute",
                    operator_id, user_id
                )

                # 发送通知
                try:
                    ModerationNotificationService.send_unmute_notification(
                        user=target_user,
                        reason=reason
                    )
                except Exception as notify_error:
                    logger.error(
                        "发送解除禁言通知失败: user_id=%s, error=%s",
                        user_id, str(notify_error)
                    )

                return {
                    'success': True,
                    'user_id': user_id,
                    'mute_record_id': mute_record.id
                }

        except Exception as e:
            logger.exception(
                "解除禁言操作失败: user_id=%s, error=%s",
                user_id, str(e)
            )
            raise

    @staticmethod
    def modify_mute_duration(
        user_id: int,
        new_duration: str,
        reason: str,
        operator_id: int,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """修改禁言时长

        修改用户的禁言时长，包括：
        1. 权限验证
        2. 查询当前生效的禁言记录
        3. 解析新时长
        4. 更新用户状态和禁言记录
        5. 设置is_manually_modified标志
        6. 取消原有Celery任务
        7. 创建操作日志
        8. 发送通知

        Args:
            user_id: 被修改禁言时长的用户ID
            new_duration: 新的时长字符串（如"3d"、"permanent"）
            reason: 修改原因
            operator_id: 操作人ID
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含修改结果的字典

        Raises:
            ValidationError: 参数验证失败
            PermissionDenied: 权限不足
            Users.DoesNotExist: 用户不存在
        """
        # 1. 参数验证
        if not reason or not reason.strip():
            raise ValidationError("修改原因不能为空")

        # 2. 查询用户对象
        try:
            target_user = Users.objects.get(id=user_id)
            operator = Users.objects.get(id=operator_id)
        except Users.DoesNotExist:
            logger.error("修改禁言时长失败：用户不存在")
            raise

        # 3. 权限验证
        if not UserModerationService.validate_permission(operator, target_user):
            raise PermissionDenied(
                f"权限不足：无法对用户 {target_user.username} 执行修改时长操作"
            )

        # 4. 查询当前生效的禁言记录
        mute_record = UserMuteRecord.objects.filter(
            user_id=user_id,
            is_active=True
        ).first()

        if not mute_record:
            raise ValidationError("用户当前未被禁言，无法修改时长")

        # 5. 解析新时长
        try:
            new_hours = DurationParser.parse(new_duration)
            new_muted_until = DurationParser.to_datetime(new_duration)
        except ValueError as e:
            logger.error("修改禁言时长失败：时长格式无效: duration=%s, error=%s", new_duration, str(e))
            raise ValidationError(str(e))

        # 6. 计算原时长（用于日志记录）
        old_hours = None
        if mute_record.muted_until:
            time_diff = mute_record.muted_until - datetime.now()
            old_hours = int(time_diff.total_seconds() / 3600)
            if old_hours < 0:
                old_hours = 0

        # 7. 使用数据库事务执行修改操作
        try:
            with transaction.atomic():
                # 更新用户表
                target_user.muted_until = new_muted_until
                target_user.save(update_fields=['muted_until'])

                logger.info(
                    "用户禁言时长已更新: user_id=%s, old_until=%s, new_until=%s",
                    user_id, mute_record.muted_until, new_muted_until
                )

                # 更新禁言记录：设置is_manually_modified标志
                mute_record.muted_until = new_muted_until
                mute_record.is_manually_modified = True
                mute_record.save(update_fields=['muted_until', 'is_manually_modified'])

                logger.info(
                    "禁言记录已更新: mute_record_id=%s, is_manually_modified=True",
                    mute_record.id
                )

                # 取消原有Celery自动解封任务（如果存在）
                if mute_record.auto_unmute_task_id:
                    try:
                        from celery import current_app
                        current_app.control.revoke(mute_record.auto_unmute_task_id, terminate=True)
                        logger.info(
                            "已取消原有自动解封任务: task_id=%s",
                            mute_record.auto_unmute_task_id
                        )
                    except Exception as celery_error:
                        logger.warning(
                            "取消自动解封任务失败: task_id=%s, error=%s",
                            mute_record.auto_unmute_task_id, str(celery_error)
                        )

                # 创建操作日志
                UserModerationLog.objects.create(
                    operator_id=operator_id,
                    target_user_id=user_id,
                    operation_type='modify_duration',
                    reason=reason,
                    duration_hours=new_hours,
                    old_duration_hours=old_hours,
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                logger.info(
                    "操作日志已创建: operator_id=%s, target_user_id=%s, operation_type=modify_duration",
                    operator_id, user_id
                )

                # 发送通知（时长变更通知）
                try:
                    ModerationNotificationService.send_mute_notification(
                        user=target_user,
                        mute_record=mute_record
                    )
                except Exception as notify_error:
                    logger.error(
                        "发送时长变更通知失败: user_id=%s, error=%s",
                        user_id, str(notify_error)
                    )

                return {
                    'success': True,
                    'user_id': user_id,
                    'mute_record_id': mute_record.id,
                    'old_hours': old_hours,
                    'new_hours': new_hours,
                    'new_muted_until': new_muted_until
                }

        except Exception as e:
            logger.exception(
                "修改禁言时长操作失败: user_id=%s, error=%s",
                user_id, str(e)
            )
            raise

    @staticmethod
    def ban_user(
        user_id: int,
        duration: str,
        reason: str,
        operator_id: int,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """封禁用户

        执行用户封禁操作，包括：
        1. 参数验证
        2. 权限验证
        3. 解析时长
        4. 更新用户状态
        5. 创建操作日志
        6. 发送通知

        Args:
            user_id: 被封禁用户ID
            duration: 时长字符串（如"3d"、"permanent"）
            reason: 封禁原因
            operator_id: 操作人ID
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含封禁结果的字典

        Raises:
            ValidationError: 参数验证失败
            PermissionDenied: 权限不足
            Users.DoesNotExist: 用户不存在
        """
        # 1. 参数验证
        if not reason or not reason.strip():
            raise ValidationError("封禁原因不能为空")

        # 2. 查询用户对象
        try:
            target_user = Users.objects.get(id=user_id)
            operator = Users.objects.get(id=operator_id)
        except Users.DoesNotExist:
            logger.error("封禁失败：用户不存在")
            raise

        # 3. 权限验证
        if not UserModerationService.validate_permission(operator, target_user):
            raise PermissionDenied(
                f"权限不足：无法对用户 {target_user.username} 执行封禁操作"
            )

        # 4. 解析时长
        try:
            hours = DurationParser.parse(duration)
            locked_until = DurationParser.to_datetime(duration)
        except ValueError as e:
            logger.error("封禁失败：时长格式无效: duration=%s, error=%s", duration, str(e))
            raise ValidationError(str(e))

        # 5. 使用数据库事务执行封禁操作
        try:
            with transaction.atomic():
                # 更新用户表
                target_user.is_active = False
                target_user.locked_until = locked_until
                target_user.ban_reason = reason
                target_user.save(update_fields=['is_active', 'locked_until', 'ban_reason'])

                logger.info(
                    "用户状态已更新: user_id=%s, is_active=False, locked_until=%s",
                    user_id, locked_until
                )

                # 创建操作日志
                UserModerationLog.objects.create(
                    operator_id=operator_id,
                    target_user_id=user_id,
                    operation_type='ban',
                    reason=reason,
                    duration_hours=hours,
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                logger.info(
                    "操作日志已创建: operator_id=%s, target_user_id=%s, operation_type=ban",
                    operator_id, user_id
                )

                # 发送通知
                try:
                    ModerationNotificationService.send_ban_notification(
                        user=target_user,
                        ban_reason=reason,
                        locked_until=locked_until
                    )
                except Exception as notify_error:
                    logger.error(
                        "发送封禁通知失败: user_id=%s, error=%s",
                        user_id, str(notify_error)
                    )

                return {
                    'success': True,
                    'user_id': user_id,
                    'locked_until': locked_until
                }

        except Exception as e:
            logger.exception(
                "封禁操作失败: user_id=%s, error=%s",
                user_id, str(e)
            )
            raise

    @staticmethod
    def unban_user(
        user_id: int,
        operator_id: int,
        reason: Optional[str] = None,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """解除封禁

        执行用户解除封禁操作，包括：
        1. 权限验证
        2. 更新用户状态
        3. 创建操作日志
        4. 发送通知

        Args:
            user_id: 被解除封禁的用户ID
            operator_id: 操作人ID
            reason: 解除原因（可选）
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含解除结果的字典

        Raises:
            ValidationError: 参数验证失败
            PermissionDenied: 权限不足
            Users.DoesNotExist: 用户不存在
        """
        # 1. 查询用户对象
        try:
            target_user = Users.objects.get(id=user_id)
            operator = Users.objects.get(id=operator_id)
        except Users.DoesNotExist:
            logger.error("解除封禁失败：用户不存在")
            raise

        # 2. 权限验证
        if not UserModerationService.validate_permission(operator, target_user):
            raise PermissionDenied(
                f"权限不足：无法对用户 {target_user.username} 执行解除封禁操作"
            )

        # 3. 使用数据库事务执行解除操作
        try:
            with transaction.atomic():
                # 更新用户表
                target_user.is_active = True
                target_user.save(update_fields=['is_active'])

                logger.info("用户状态已更新: user_id=%s, is_active=True", user_id)

                # 创建操作日志
                UserModerationLog.objects.create(
                    operator_id=operator_id,
                    target_user_id=user_id,
                    operation_type='unban',
                    reason=reason or '手动解除封禁',
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                logger.info(
                    "操作日志已创建: operator_id=%s, target_user_id=%s, operation_type=unban",
                    operator_id, user_id
                )

                # 发送通知
                try:
                    ModerationNotificationService.send_unban_notification(
                        user=target_user,
                        reason=reason
                    )
                except Exception as notify_error:
                    logger.error(
                        "发送解除封禁通知失败: user_id=%s, error=%s",
                        user_id, str(notify_error)
                    )

                return {
                    'success': True,
                    'user_id': user_id
                }

        except Exception as e:
            logger.exception(
                "解除封禁操作失败: user_id=%s, error=%s",
                user_id, str(e)
            )
            raise

    @staticmethod
    def modify_ban_duration(
        user_id: int,
        new_duration: str,
        reason: str,
        operator_id: int,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """修改封禁时长

        修改用户的封禁时长，包括：
        1. 权限验证
        2. 解析新时长
        3. 更新用户状态
        4. 创建操作日志
        5. 发送通知

        Args:
            user_id: 被修改封禁时长的用户ID
            new_duration: 新的时长字符串（如"3d"、"permanent"）
            reason: 修改原因
            operator_id: 操作人ID
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含修改结果的字典

        Raises:
            ValidationError: 参数验证失败
            PermissionDenied: 权限不足
            Users.DoesNotExist: 用户不存在
        """
        # 1. 参数验证
        if not reason or not reason.strip():
            raise ValidationError("修改原因不能为空")

        # 2. 查询用户对象
        try:
            target_user = Users.objects.get(id=user_id)
            operator = Users.objects.get(id=operator_id)
        except Users.DoesNotExist:
            logger.error("修改封禁时长失败：用户不存在")
            raise

        # 3. 权限验证
        if not UserModerationService.validate_permission(operator, target_user):
            raise PermissionDenied(
                f"权限不足：无法对用户 {target_user.username} 执行修改时长操作"
            )

        # 4. 检查用户是否被封禁
        if target_user.is_active:
            raise ValidationError("用户当前未被封禁，无法修改时长")

        # 5. 解析新时长
        try:
            new_hours = DurationParser.parse(new_duration)
            new_locked_until = DurationParser.to_datetime(new_duration)
        except ValueError as e:
            logger.error("修改封禁时长失败：时长格式无效: duration=%s, error=%s", new_duration, str(e))
            raise ValidationError(str(e))

        # 6. 计算原时长（用于日志记录）
        old_hours = None
        if target_user.locked_until:
            time_diff = target_user.locked_until - datetime.now()
            old_hours = int(time_diff.total_seconds() / 3600)
            if old_hours < 0:
                old_hours = 0

        # 7. 使用数据库事务执行修改操作
        try:
            with transaction.atomic():
                # 更新用户表
                old_locked_until = target_user.locked_until
                target_user.locked_until = new_locked_until
                target_user.save(update_fields=['locked_until'])

                logger.info(
                    "用户封禁时长已更新: user_id=%s, old_until=%s, new_until=%s",
                    user_id, old_locked_until, new_locked_until
                )

                # 创建操作日志
                UserModerationLog.objects.create(
                    operator_id=operator_id,
                    target_user_id=user_id,
                    operation_type='modify_duration',
                    reason=reason,
                    duration_hours=new_hours,
                    old_duration_hours=old_hours,
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                logger.info(
                    "操作日志已创建: operator_id=%s, target_user_id=%s, operation_type=modify_duration",
                    operator_id, user_id
                )

                # 发送通知（时长变更通知）
                try:
                    ModerationNotificationService.send_ban_notification(
                        user=target_user,
                        ban_reason=target_user.ban_reason or '封禁时长已修改',
                        locked_until=new_locked_until
                    )
                except Exception as notify_error:
                    logger.error(
                        "发送时长变更通知失败: user_id=%s, error=%s",
                        user_id, str(notify_error)
                    )

                return {
                    'success': True,
                    'user_id': user_id,
                    'old_hours': old_hours,
                    'new_hours': new_hours,
                    'new_locked_until': new_locked_until
                }

        except Exception as e:
            logger.exception(
                "修改封禁时长操作失败: user_id=%s, error=%s",
                user_id, str(e)
            )
            raise

    @staticmethod
    def batch_mute(
        user_ids: list,
        duration: str,
        reason: str,
        operator_id: int,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """批量禁言

        批量禁言多个用户，限制最多20个用户。
        对每个用户执行权限验证，创建独立的禁言记录。
        创建一条操作日志，extra_data包含所有用户ID列表。

        Args:
            user_ids: 被禁言用户ID列表
            duration: 时长字符串（如"3d"、"permanent"）
            reason: 禁言原因
            operator_id: 操作人ID
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含批量操作结果的字典

        Raises:
            ValidationError: 参数验证失败（如超过20个用户）
        """
        # 1. 验证用户数量
        if not user_ids:
            raise ValidationError("用户ID列表不能为空")

        if len(user_ids) > 20:
            raise ValidationError("批量操作最多支持20个用户")

        # 2. 参数验证
        if not reason or not reason.strip():
            raise ValidationError("禁言原因不能为空")

        # 3. 执行批量操作
        results = []
        success_count = 0
        failed_count = 0

        for user_id in user_ids:
            try:
                result = UserModerationService.mute_user(
                    user_id=user_id,
                    duration=duration,
                    reason=reason,
                    operator_id=operator_id,
                    mute_type='manual',
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                results.append({
                    'user_id': user_id,
                    'success': True,
                    'message': '禁言成功'
                })
                success_count += 1
            except Exception as e:
                results.append({
                    'user_id': user_id,
                    'success': False,
                    'message': str(e)
                })
                failed_count += 1
                logger.warning(
                    "批量禁言：用户 %s 操作失败: %s",
                    user_id, str(e)
                )

        # 4. 创建批量操作日志
        try:
            hours = DurationParser.parse(duration)
        except ValueError:
            hours = None

        try:
            UserModerationLog.objects.create(
                operator_id=operator_id,
                target_user_id=user_ids[0],  # 使用第一个用户ID作为目标
                operation_type='mute',
                reason=f"批量禁言：{reason}",
                duration_hours=hours,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={'user_ids': user_ids, 'batch_operation': True}
            )
            logger.info(
                "批量禁言操作日志已创建: operator_id=%s, user_count=%s",
                operator_id, len(user_ids)
            )
        except Exception as log_error:
            logger.error(
                "创建批量操作日志失败: error=%s",
                str(log_error)
            )

        return {
            'success': True,
            'total': len(user_ids),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }

    @staticmethod
    def batch_ban(
        user_ids: list,
        duration: str,
        reason: str,
        operator_id: int,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """批量封禁

        批量封禁多个用户，限制最多20个用户。
        对每个用户执行权限验证。
        创建一条操作日志，extra_data包含所有用户ID列表。

        Args:
            user_ids: 被封禁用户ID列表
            duration: 时长字符串（如"3d"、"permanent"）
            reason: 封禁原因
            operator_id: 操作人ID
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含批量操作结果的字典

        Raises:
            ValidationError: 参数验证失败（如超过20个用户）
        """
        # 1. 验证用户数量
        if not user_ids:
            raise ValidationError("用户ID列表不能为空")

        if len(user_ids) > 20:
            raise ValidationError("批量操作最多支持20个用户")

        # 2. 参数验证
        if not reason or not reason.strip():
            raise ValidationError("封禁原因不能为空")

        # 3. 执行批量操作
        results = []
        success_count = 0
        failed_count = 0

        for user_id in user_ids:
            try:
                result = UserModerationService.ban_user(
                    user_id=user_id,
                    duration=duration,
                    reason=reason,
                    operator_id=operator_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                results.append({
                    'user_id': user_id,
                    'success': True,
                    'message': '封禁成功'
                })
                success_count += 1
            except Exception as e:
                results.append({
                    'user_id': user_id,
                    'success': False,
                    'message': str(e)
                })
                failed_count += 1
                logger.warning(
                    "批量封禁：用户 %s 操作失败: %s",
                    user_id, str(e)
                )

        # 4. 创建批量操作日志
        try:
            hours = DurationParser.parse(duration)
        except ValueError:
            hours = None

        try:
            UserModerationLog.objects.create(
                operator_id=operator_id,
                target_user_id=user_ids[0],
                operation_type='ban',
                reason=f"批量封禁：{reason}",
                duration_hours=hours,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={'user_ids': user_ids, 'batch_operation': True}
            )
            logger.info(
                "批量封禁操作日志已创建: operator_id=%s, user_count=%s",
                operator_id, len(user_ids)
            )
        except Exception as log_error:
            logger.error(
                "创建批量操作日志失败: error=%s",
                str(log_error)
            )

        return {
            'success': True,
            'total': len(user_ids),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }

    @staticmethod
    def batch_unmute(
        user_ids: list,
        operator_id: int,
        reason: Optional[str] = None,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """批量解除禁言

        批量解除多个用户的禁言，限制最多20个用户。
        对每个用户执行权限验证。
        创建一条操作日志，extra_data包含所有用户ID列表。

        Args:
            user_ids: 被解除禁言用户ID列表
            operator_id: 操作人ID
            reason: 解除原因（可选）
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含批量操作结果的字典

        Raises:
            ValidationError: 参数验证失败（如超过20个用户）
        """
        # 1. 验证用户数量
        if not user_ids:
            raise ValidationError("用户ID列表不能为空")

        if len(user_ids) > 20:
            raise ValidationError("批量操作最多支持20个用户")

        # 2. 执行批量操作
        results = []
        success_count = 0
        failed_count = 0

        for user_id in user_ids:
            try:
                result = UserModerationService.unmute_user(
                    user_id=user_id,
                    operator_id=operator_id,
                    reason=reason,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                results.append({
                    'user_id': user_id,
                    'success': True,
                    'message': '解除禁言成功'
                })
                success_count += 1
            except Exception as e:
                results.append({
                    'user_id': user_id,
                    'success': False,
                    'message': str(e)
                })
                failed_count += 1
                logger.warning(
                    "批量解除禁言：用户 %s 操作失败: %s",
                    user_id, str(e)
                )

        # 3. 创建批量操作日志
        try:
            UserModerationLog.objects.create(
                operator_id=operator_id,
                target_user_id=user_ids[0],
                operation_type='unmute',
                reason=f"批量解除禁言：{reason or '手动解除'}",
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={'user_ids': user_ids, 'batch_operation': True}
            )
            logger.info(
                "批量解除禁言操作日志已创建: operator_id=%s, user_count=%s",
                operator_id, len(user_ids)
            )
        except Exception as log_error:
            logger.error(
                "创建批量操作日志失败: error=%s",
                str(log_error)
            )

        return {
            'success': True,
            'total': len(user_ids),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }

    @staticmethod
    def batch_unban(
        user_ids: list,
        operator_id: int,
        reason: Optional[str] = None,
        ip_address: str = '',
        user_agent: str = ''
    ) -> Dict[str, Any]:
        """批量解除封禁

        批量解除多个用户的封禁，限制最多20个用户。
        对每个用户执行权限验证。
        创建一条操作日志，extra_data包含所有用户ID列表。

        Args:
            user_ids: 被解除封禁用户ID列表
            operator_id: 操作人ID
            reason: 解除原因（可选）
            ip_address: 操作人IP地址
            user_agent: 操作人User-Agent

        Returns:
            dict: 包含批量操作结果的字典

        Raises:
            ValidationError: 参数验证失败（如超过20个用户）
        """
        # 1. 验证用户数量
        if not user_ids:
            raise ValidationError("用户ID列表不能为空")

        if len(user_ids) > 20:
            raise ValidationError("批量操作最多支持20个用户")

        # 2. 执行批量操作
        results = []
        success_count = 0
        failed_count = 0

        for user_id in user_ids:
            try:
                result = UserModerationService.unban_user(
                    user_id=user_id,
                    operator_id=operator_id,
                    reason=reason,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                results.append({
                    'user_id': user_id,
                    'success': True,
                    'message': '解除封禁成功'
                })
                success_count += 1
            except Exception as e:
                results.append({
                    'user_id': user_id,
                    'success': False,
                    'message': str(e)
                })
                failed_count += 1
                logger.warning(
                    "批量解除封禁：用户 %s 操作失败: %s",
                    user_id, str(e)
                )

        # 3. 创建批量操作日志
        try:
            UserModerationLog.objects.create(
                operator_id=operator_id,
                target_user_id=user_ids[0],
                operation_type='unban',
                reason=f"批量解除封禁：{reason or '手动解除'}",
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={'user_ids': user_ids, 'batch_operation': True}
            )
            logger.info(
                "批量解除封禁操作日志已创建: operator_id=%s, user_count=%s",
                operator_id, len(user_ids)
            )
        except Exception as log_error:
            logger.error(
                "创建批量操作日志失败: error=%s",
                str(log_error)
            )

        return {
            'success': True,
            'total': len(user_ids),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }
