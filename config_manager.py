import json
import os
import sys
from pathlib import Path
from typing import Optional

class ConfigManager:
    """配置管理器，用于保存和读取用户配置"""

    def __init__(self):
        # 如果是打包后的单文件 exe (sys.frozen = True)，则使用 exe 所在目录
        # 否则使用当前脚本所在目录（开发环境）。
        if getattr(sys, 'frozen', False):
            self.exe_dir = Path(sys.executable).parent
        else:
            self.exe_dir = Path(os.path.dirname(os.path.abspath(__file__)))

        # 指定 config.json 存放位置 => 和 exe 同目录
        self.config_path = self.exe_dir / 'config.json'

        # 先尝试加载，如不存在则自动生成空结构
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置文件，如不存在则创建空文件"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"读取配置文件时出错: {str(e)}")
                return {}
        else:
            # 文件不存在，先创建一个空配置并保存
            print("未找到 config.json，已自动创建空配置文件。")
            self._save_config()
            return {}

    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件时出错: {str(e)}")
    
    def get_sai_path(self) -> Optional[str]:
        """获取SAI路径"""
        return self.config.get('sai_path')
    
    def set_sai_path(self, path: str) -> None:
        """设置SAI路径"""
        self.config['sai_path'] = path
        self._save_config()
    
    def get_last_import_path(self) -> Optional[str]:
        """获取上次导入路径"""
        return self.config.get('last_import_path')
    
    def set_last_import_path(self, path: str) -> None:
        """设置上次导入路径"""
        self.config['last_import_path'] = path
        self._save_config()
