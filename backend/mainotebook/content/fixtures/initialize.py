# -*- coding: utf-8 -*-

import os
import django
from dvadmin.utils.core_initialize import CoreInitialize


class Initialize(CoreInitialize):

    def run(self):
        """
        script: python manage.py init_ai_model
        """
        self.init_ai_model()

    def init_ai_model(self):
        """
        初始化 AI 模型数据
        """
        from mainotebook.content.models import AIModel
        self.save(
            AIModel,
            self.load_data("init_ai_model.json"),
            name="AI模型"
        )

    def load_data(self, filename):
        import json
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            filename,
        )
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 提取 fields 字段作为数据
            result = []
            for item in data:
                fields = item.get('fields', {})
                if 'pk' in item:
                    fields['id'] = item['pk']
                result.append(fields)
            return result
