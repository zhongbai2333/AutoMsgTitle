import json
import os

class JsonDataEditor:
    def __init__(self, filepath='./config/data.json'):
        self.filepath = filepath
        # 检查文件是否存在，如果不存在则创建空的JSON文件
        if not os.path.exists(filepath):
            self._write_data({})

    def _read_data(self):
        """读取 JSON 文件内容并返回一个字典"""
        with open(self.filepath, 'r') as file:
            return json.load(file)

    def _write_data(self, data):
        """将字典写入 JSON 文件"""
        with open(self.filepath, 'w') as file:
            json.dump(data, file, indent=4)

    def list(self):
        """获取当前 JSON 文件中的数据"""
        return self._read_data()

    def add(self, key, value):
        """向 JSON 文件中添加新的数据项"""
        if not os.path.exists(self.filepath):
            self._write_data({})
        data = self._read_data()
        data[key] = value
        self._write_data(data)

    def remove(self, key):
        from .__init__ import debug_print
        """从 JSON 文件中删除数据项"""
        data = self._read_data()
        if key in data:
            del data[key]
            self._write_data(data)
        else:
            debug_print(f"Key '{key}' not found in data.")