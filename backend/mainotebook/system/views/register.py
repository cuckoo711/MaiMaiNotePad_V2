# -*- coding: utf-8 -*-

"""
注册相关的序列化器、频率限制类和视图

包含用户注册表单校验、注册和重发验证邮件的频率限制。
"""

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from mainotebook.system.services.email_service import EmailService
from mainotebook.system.services.registration import RegistrationService
from mainotebook.utils.json_response import DetailResponse, ErrorResponse


class RegisterSerializer(serializers.Serializer):
    """注册表单序列化器

    校验用户提交的注册信息：邮箱格式、用户名长度、密码长度。
    """

    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "请输入有效的邮箱地址",
            "invalid": "请输入有效的邮箱地址",
            "blank": "请输入有效的邮箱地址",
        },
    )
    username = serializers.CharField(
        required=True,
        min_length=3,
        max_length=30,
        error_messages={
            "required": "用户名长度需在 3-30 个字符之间",
            "blank": "用户名长度需在 3-30 个字符之间",
            "min_length": "用户名长度需在 3-30 个字符之间",
            "max_length": "用户名长度需在 3-30 个字符之间",
        },
    )
    password = serializers.CharField(
        required=True,
        min_length=6,
        write_only=True,
        error_messages={
            "required": "密码长度至少为 6 个字符",
            "blank": "密码长度至少为 6 个字符",
            "min_length": "密码长度至少为 6 个字符",
        },
    )


class RegisterRateThrottle(AnonRateThrottle):
    """注册接口频率限制

    同一 IP 地址每小时最多允许 10 次注册请求。
    """

    rate = "10/hour"
    scope = "register"


class ResendVerificationRateThrottle(AnonRateThrottle):
    """重发验证邮件频率限制

    同一 IP 地址每小时最多允许 5 次重发请求。
    """

    rate = "5/hour"
    scope = "resend_verification"


class RegisterView(APIView):
    """注册视图

    处理用户注册请求：校验输入 → 检查唯一性 → 存 Redis → 发邮件 → 返回结果。
    无需认证，对匿名用户开放。
    """

    authentication_classes = []
    permission_classes = []
    throttle_classes = [RegisterRateThrottle]

    def post(self, request: Request) -> Response:
        """处理注册请求

        Args:
            request: HTTP 请求对象，包含 email、username、password

        Returns:
            Response: 成功返回 DetailResponse，失败返回 ErrorResponse
        """
        # 打印请求数据用于调试
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"注册请求数据: {request.data}")
        logger.info(f"Content-Type: {request.content_type}")
        
        # 1. 校验输入
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            # 取第一个字段的第一条错误信息
            first_field_errors = next(iter(serializer.errors.values()))
            first_error = first_field_errors[0] if first_field_errors else "请求参数错误"
            logger.warning(f"注册校验失败: {first_error}")
            return ErrorResponse(msg=str(first_error))

        email = serializer.validated_data["email"]
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        # 2. 检查邮箱/用户名唯一性
        error_msg = RegistrationService.check_uniqueness(email, username)
        if error_msg:
            logger.warning(f"注册唯一性检查失败: {error_msg}")
            return ErrorResponse(msg=error_msg)

        # 3. 将注册信息暂存到 Redis
        token = RegistrationService.store_pending_registration(email, username, password)

        # 4. 发送验证邮件
        try:
            # 获取前端验证链接前缀（可选）
            verification_url = request.data.get("verification_url")
            logger.info(f"准备发送验证邮件: email={email}, verification_url={verification_url}")
            success, send_error = EmailService.send_verification_email(email, username, token, verification_url)
            if not success:
                logger.error(f"验证邮件发送失败: {send_error}")
                return ErrorResponse(msg=send_error, code=500, status=500)
        except Exception as e:
            logger.exception(f"发送验证邮件过程中发生异常: {str(e)}")
            return ErrorResponse(msg=f"系统错误: {str(e)}", code=500, status=500)

        # 5. 返回成功响应
        return DetailResponse(data={"message": "验证邮件已发送，请查收邮箱"})


class VerifyEmailView(APIView):
    """邮箱验证视图

    处理用户点击验证链接后的请求：从 Redis 读取注册信息，
    创建用户，分配部门角色，删除 Redis key，签发 JWT。
    无需认证，对匿名用户开放。
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request) -> Response:
        """处理邮箱验证请求

        Args:
            request: HTTP 请求对象，查询参数中包含 token

        Returns:
            Response: 成功返回 JWT 令牌和用户信息，失败返回 reason 字段
        """
        token = request.query_params.get("token")
        if not token:
            return ErrorResponse(msg="缺少验证令牌参数", status=400)

        success, result = RegistrationService.verify_and_create_user(token)
        if success:
            return DetailResponse(data=result)
        else:
            return ErrorResponse(
                data={"reason": result["reason"]},
                msg=result["msg"],
                status=400,
            )



class ResendVerificationView(APIView):
    """重发验证邮件视图

    处理重发验证邮件请求：从 Redis 读取 pending 数据，
    生成新 token，发送验证邮件。
    无论邮箱是否存在均返回成功响应，防止邮箱枚举攻击。
    """

    authentication_classes = []
    permission_classes = []
    throttle_classes = [ResendVerificationRateThrottle]

    def post(self, request: Request) -> Response:
        """处理重发验证邮件请求

        Args:
            request: HTTP 请求对象，包含 email

        Returns:
            Response: 始终返回成功的 DetailResponse
        """
        email = request.data.get("email", "").strip()
        verification_url = request.data.get("verification_url")

        if email:
            # 尝试重发验证邮件
            result = RegistrationService.resend_verification(email)
            if result:
                new_token, username = result
                EmailService.send_verification_email(email, username, new_token, verification_url)

        # 无论邮箱是否存在，均返回成功响应（防止邮箱枚举攻击）
        return DetailResponse(data={"message": "验证邮件已重新发送"})

