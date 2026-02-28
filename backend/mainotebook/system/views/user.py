import hashlib
import os
import uuid
from django.core.files.storage import default_storage
from django.conf import settings

from django.contrib.auth.hashers import make_password, check_password
from django_restql.fields import DynamicSerializerMethodField
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import connection
from django.db.models import Q
from application import dispatch
from mainotebook.system.models import Users, Role, Dept
from mainotebook.system.views.role import RoleSerializer
from mainotebook.utils.json_response import ErrorResponse, DetailResponse, SuccessResponse
from mainotebook.utils.serializers import CustomModelSerializer
from mainotebook.utils.validator import CustomUniqueValidator
from mainotebook.utils.viewset import CustomModelViewSet


def recursion(instance, parent, result):
    new_instance = getattr(instance, parent, None)
    res = []
    data = getattr(instance, result, None)
    if data:
        res.append(data)
    if new_instance:
        array = recursion(new_instance, parent, result)
        res += array
    return res


class FileOrStringField(serializers.Field):
    """
    自定义字段：支持文件对象或字符串
    """
    def to_internal_value(self, data):
        # 如果是文件对象，直接返回
        if hasattr(data, 'read'):
            return data
        # 如果是字符串，返回字符串
        return str(data)

    def to_representation(self, value):
        if not value:
            return None
        return str(value)


class UserSerializer(CustomModelSerializer):
    """
    用户管理-序列化器
    """
    dept_name = serializers.CharField(source='dept.name', read_only=True)
    role_info = DynamicSerializerMethodField()
    dept_name_all = serializers.SerializerMethodField()

    class Meta:
        model = Users
        read_only_fields = ["id"]
        exclude = ["password"]
        extra_kwargs = {
            "post": {"required": False},
            "mobile": {"required": False},
        }

    def get_dept_name_all(self, instance):
        dept_name_all = recursion(instance.dept, "parent", "name")
        dept_name_all.reverse()
        return "/".join(dept_name_all)

    def get_role_info(self, instance, parsed_query):
        roles = instance.role.all()
        # You can do what ever you want in here
        # `parsed_query` param is passed to BookSerializer to allow further querying
        serializer = RoleSerializer(
            roles,
            many=True,
            parsed_query=parsed_query
        )
        return serializer.data


class UserCreateSerializer(CustomModelSerializer):
    """
    用户新增-序列化器
    """

    username = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message="账号必须唯一")
        ],
    )
    password = serializers.CharField(
        required=False,
    )

    def validate_password(self, value):
        """
        对密码进行验证
        """
        md5 = hashlib.md5()
        md5.update(value.encode('utf-8'))
        md5_password = md5.hexdigest()
        return make_password(md5_password)

    def save(self, **kwargs):
        data = super().save(**kwargs)
        data.dept_belong_id = data.dept_id
        data.save()
        if not self.validated_data.get('manage_dept', None):
            data.manage_dept.add(data.dept_id)
        data.post.set(self.initial_data.get("post", []))
        return data

    class Meta:
        model = Users
        fields = "__all__"
        read_only_fields = ["id"]
        extra_kwargs = {
            "post": {"required": False},
            "mobile": {"required": False},
        }


class UserUpdateSerializer(CustomModelSerializer):
    """
    用户修改-序列化器
    """

    username = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message="账号必须唯一")
        ],
    )

    def validate_is_active(self, value):
        """
        更改激活状态
        """
        if value:
            self.initial_data["login_error_count"] = 0
        return value

    def save(self, **kwargs):
        data = super().save(**kwargs)
        data.dept_belong_id = data.dept_id
        data.save()
        if not self.validated_data.get('manage_dept', None):
            data.manage_dept.add(data.dept_id)
        data.post.set(self.initial_data.get("post", []))
        return data

    class Meta:
        model = Users
        read_only_fields = ["id", "password"]
        fields = "__all__"
        extra_kwargs = {
            "post": {"required": False, "read_only": True},
            "mobile": {"required": False},
        }


class UserInfoUpdateSerializer(CustomModelSerializer):
    """
    用户信息修改-序列化器

    支持修改用户名、性别、手机号、邮箱、头像。
    用户名（username）需唯一校验，姓名（name）字段已弃用。
    """
    username = serializers.CharField(
        max_length=150,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message="该用户名已被使用")
        ],
        required=False
    )
    mobile = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message="手机号必须唯一")
        ],
        allow_blank=True,
        required=False
    )
    avatar = FileOrStringField(required=False, allow_null=True)

    def update(self, instance, validated_data):
        # 处理头像上传
        avatar_data = validated_data.get('avatar')
        if avatar_data and hasattr(avatar_data, 'read'):
            # 生成文件名
            ext = os.path.splitext(avatar_data.name)[1]
            if not ext:
                ext = '.jpg'
            filename = f"avatar/{uuid.uuid4()}{ext}"
            # 保存文件
            path = default_storage.save(filename, avatar_data)
            # 构建完整URL
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            full_path = os.path.join(media_url, path).replace('\\', '/')
            validated_data['avatar'] = full_path
            # 更新头像更新时间
            from django.utils import timezone
            validated_data['avatar_updated_at'] = timezone.now()
        elif avatar_data == '':
            # 删除头像时也更新时间
            from django.utils import timezone
            validated_data['avatar_updated_at'] = timezone.now()
            
        return super().update(instance, validated_data)

    class Meta:
        model = Users
        fields = ['username', 'email', 'mobile', 'avatar', 'gender', 'avatar_updated_at']
        extra_kwargs = {
            "post": {"required": False, "read_only": True},
            "mobile": {"required": False},
            "avatar_updated_at": {"read_only": True},
        }


class ExportUserProfileSerializer(CustomModelSerializer):
    """
    用户导出 序列化器
    """

    last_login = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False, read_only=True
    )
    is_active = serializers.SerializerMethodField(read_only=True)
    dept_name = serializers.CharField(source="dept.name", default="")
    dept_owner = serializers.CharField(source="dept.owner", default="")
    gender = serializers.CharField(source="get_gender_display", read_only=True)

    def get_is_active(self, instance):
        return "启用" if instance.is_active else "停用"

    class Meta:
        model = Users
        fields = (
            "username",
            "name",
            "email",
            "mobile",
            "gender",
            "is_active",
            "last_login",
            "dept_name",
            "dept_owner",
        )


class UserProfileImportSerializer(CustomModelSerializer):
    password = serializers.CharField(read_only=True, required=False)

    def save(self, **kwargs):
        data = super().save(**kwargs)
        password = hashlib.new(
            "md5", str(self.initial_data.get("password", "admin123456")).encode(encoding="UTF-8")
        ).hexdigest()
        data.set_password(password)
        data.save()
        return data

    class Meta:
        model = Users
        exclude = (
            "post",
            "user_permissions",
            "groups",
            "is_superuser",
            "date_joined",
        )


class UserViewSet(CustomModelViewSet):
    """
    用户接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """

    queryset = Users.objects.exclude(is_superuser=1).all()
    serializer_class = UserSerializer
    create_serializer_class = UserCreateSerializer
    update_serializer_class = UserUpdateSerializer
    filter_fields = ["name", "username", "gender", "is_active", "dept", "user_type"]
    search_fields = ["username", "name", "dept__name", "role__name"]
    # 导出
    export_field_label = {
        "username": "用户账号",
        "name": "用户名称",
        "email": "用户邮箱",
        "mobile": "手机号码",
        "gender": "用户性别",
        "is_active": "帐号状态",
        "last_login": "最后登录时间",
        "dept_name": "部门名称",
        "dept_owner": "部门负责人",
    }
    export_serializer_class = ExportUserProfileSerializer
    # 导入
    import_serializer_class = UserProfileImportSerializer
    import_field_dict = {
        "username": "登录账号",
        "name": "用户名称",
        "email": "用户邮箱",
        "mobile": "手机号码",
        "gender": {
            "title": "用户性别",
            "choices": {
                "data": {"未知": 2, "男": 1, "女": 0},
            }
        },
        "is_active": {
            "title": "帐号状态",
            "choices": {
                "data": {"启用": True, "禁用": False},
            }
        },
        "dept": {"title": "部门", "choices": {"queryset": Dept.objects.filter(status=True), "values_name": "name"}},
        "role": {"title": "角色", "choices": {"queryset": Role.objects.filter(status=True), "values_name": "name"}},
    }

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def user_info(self, request):
        """获取当前用户信息
        
        Returns:
            Response: 包含用户基本信息、部门、角色及管理员标识
        """
        user = request.user
        # 判断是否为管理角色（超级管理员、管理员、审核员）
        ADMIN_ROLE_KEYS = {'superadmin', 'admin', 'reviewer'}
        user_role_keys = set(user.role.values_list('key', flat=True))
        is_admin = user.is_superuser or bool(user_role_keys & ADMIN_ROLE_KEYS)
        result = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "mobile": user.mobile,
            "user_type": user.user_type,
            "gender": user.gender,
            "email": user.email,
            "avatar": user.avatar,
            "avatar_updated_at": user.avatar_updated_at.isoformat() if user.avatar_updated_at else None,
            "dept": user.dept_id,
            "is_superuser": user.is_superuser,
            "is_admin": is_admin,
            "role": user.role.values_list('id', flat=True),
            "pwd_change_count":user.pwd_change_count
        }
        if hasattr(connection, 'tenant'):
            result['tenant_id'] = connection.tenant and connection.tenant.id
            result['tenant_name'] = connection.tenant and connection.tenant.name
        dept = getattr(user, 'dept', None)
        if dept:
            result['dept_info'] = {
                'dept_id': dept.id,
                'dept_name': dept.name
            }
        else:
            result['dept_info'] = {
                'dept_id': None,
                'dept_name': "暂无部门"
            }
        role = getattr(user, 'role', None)
        if role:
            result['role_info'] = role.values('id', 'name', 'key')
        return DetailResponse(data=result, msg="获取成功")

    @action(methods=["PUT"], detail=False, permission_classes=[IsAuthenticated])
    def update_user_info(self, request):
        """修改当前用户信息

        如果请求中包含 email 字段且与当前邮箱不同，
        则需要同时提供 email_code 进行验证码校验。
        """
        user = request.user
        data = request.data

        # 如果修改了邮箱，需要校验验证码
        new_email = data.get("email")
        if new_email and new_email != user.email:
            email_code = data.get("email_code", "")
            if not email_code:
                return ErrorResponse(msg="修改邮箱需要提供验证码")

            from mainotebook.system.services.email_code_service import verify_email_code
            ok, err_msg = verify_email_code(user.id, new_email, email_code)
            if not ok:
                return ErrorResponse(msg=err_msg)

            # 检查新邮箱是否已被其他用户使用
            if Users.objects.filter(email=new_email).exclude(id=user.id).exists():
                return ErrorResponse(msg="该邮箱已被其他用户使用")

        serializer = UserInfoUpdateSerializer(user, data=data, request=request, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return DetailResponse(data=None, msg="修改成功")

    @action(methods=["POST"], detail=False, permission_classes=[IsAuthenticated])
    def send_email_code(self, request):
        """发送邮箱验证码

        向指定邮箱发送 6 位数字验证码，有效期 5 分钟。
        同一用户重复请求会覆盖旧验证码。
        """
        email = request.data.get("email", "").strip()
        if not email:
            return ErrorResponse(msg="请输入邮箱地址")

        # 简单格式校验
        from rest_framework.serializers import EmailField
        try:
            EmailField().run_validation(email)
        except Exception:
            return ErrorResponse(msg="请输入有效的邮箱地址")

        # 检查邮箱是否已被其他用户使用
        if Users.objects.filter(email=email).exclude(id=request.user.id).exists():
            return ErrorResponse(msg="该邮箱已被其他用户使用")

        from mainotebook.system.services.email_code_service import store_email_code, send_email_code
        code = store_email_code(request.user.id, email)
        ok, err_msg = send_email_code(email, code)
        if not ok:
            return ErrorResponse(msg=err_msg)

        return DetailResponse(data=None, msg="验证码已发送")

    @action(methods=["PUT"], detail=False, permission_classes=[IsAuthenticated])
    def change_password(self, request, *args, **kwargs):
        """密码修改"""
        data = request.data
        old_pwd = data.get("oldPassword")
        new_pwd = data.get("newPassword")
        new_pwd2 = data.get("newPassword2")
        if old_pwd is None or new_pwd is None or new_pwd2 is None:
            return ErrorResponse(msg="参数不能为空")
        if new_pwd != new_pwd2:
            return ErrorResponse(msg="两次密码不匹配")
        verify_password = check_password(old_pwd, request.user.password)
        if not verify_password:
            old_pwd_md5 = hashlib.md5(old_pwd.encode(encoding='UTF-8')).hexdigest()
            verify_password = check_password(str(old_pwd_md5), request.user.password)
            # 创建用户时、自定义密码无法修改问题
            if not verify_password:
                old_pwd_md5 = hashlib.md5(old_pwd_md5.encode(encoding='UTF-8')).hexdigest()
                verify_password = check_password(str(old_pwd_md5), request.user.password)
        if verify_password:
            # request.user.password = make_password(hashlib.md5(new_pwd.encode(encoding='UTF-8')).hexdigest())
            request.user.password = make_password(hashlib.md5(new_pwd.encode(encoding='UTF-8')).hexdigest())
            request.user.pwd_change_count += 1
            request.user.save()
            return DetailResponse(data=None, msg="修改成功")
        else:
            return ErrorResponse(msg="旧密码不正确")

    @action(methods=["post"], detail=False, permission_classes=[IsAuthenticated])
    def login_change_password(self, request, *args, **kwargs):
        """初次登录进行密码修改"""
        data = request.data
        new_pwd = data.get("password")
        new_pwd2 = data.get("password_regain")
        if new_pwd != new_pwd2:
            return ErrorResponse(msg="两次密码不匹配")
        else:
            request.user.password = make_password(new_pwd)
            request.user.pwd_change_count += 1
            request.user.save()
            return DetailResponse(data=None, msg="修改成功")

    @action(methods=["PUT"], detail=True, permission_classes=[IsAuthenticated])
    def reset_to_default_password(self, request,pk):
        """恢复默认密码"""
        if not self.request.user.is_superuser:
            return ErrorResponse(msg="只允许超级管理员对其进行密码重置")
        instance = Users.objects.filter(id=pk).first()
        if instance:
            default_password = dispatch.get_system_config_values("base.default_password")
            md5_pwd = hashlib.md5(default_password.encode(encoding='UTF-8')).hexdigest()
            instance.password = make_password(md5_pwd)
            instance.save()
            return DetailResponse(data=None, msg="密码重置成功")
        else:
            return ErrorResponse(msg="未获取到用户")

    @action(methods=["PUT"], detail=True)
    def reset_password(self, request, pk):
        """
        密码重置
        """
        if not self.request.user.is_superuser:
            return ErrorResponse(msg="只允许超级管理员对其进行密码重置")
        instance = Users.objects.filter(id=pk).first()
        data = request.data
        new_pwd = data.get("newPassword")
        new_pwd2 = data.get("newPassword2")
        if instance:
            if new_pwd != new_pwd2:
                return ErrorResponse(msg="两次密码不匹配")
            else:
                instance.password = make_password(new_pwd)
                instance.save()
                return DetailResponse(data=None, msg="修改成功")
        else:
            return ErrorResponse(msg="未获取到用户")

    def list(self, request, *args, **kwargs):
        dept_id = request.query_params.get('dept')
        show_all = request.query_params.get('show_all')
        if not dept_id:
            dept_id = ''
        if not show_all:
            show_all = 0
        if int(show_all):
            all_did = [dept_id]
            def inner(did):
                sub = Dept.objects.filter(parent_id=did)
                if not sub.exists():
                    return
                for i in sub:
                    all_did.append(i.pk)
                    inner(i)
            if dept_id != '':
                inner(dept_id)
                searchs = [
                    Q(**{f+'__icontains':i})
                    for f in self.search_fields
                ] if (i:=request.query_params.get('search')) else []
                q_obj = []
                if searchs:
                    q = searchs[0]
                    for i in searchs[1:]:
                        q |= i
                    q_obj.append(Q(q))
                queryset = Users.objects.filter(*q_obj, dept_id__in=all_did)
            else:
                queryset = self.filter_queryset(self.get_queryset())
        else:
            queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, request=request)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg="获取成功")
