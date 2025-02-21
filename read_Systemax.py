import os
import numpy as np
from tkinter import filedialog, Tk
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import graphviz
from pathlib import Path
import shutil
from config_manager import ConfigManager
import sys

@dataclass
class BrushData:
    """笔刷数据结构"""
    name: str
    values: np.ndarray
    indices: np.ndarray
    sub_brushes: Dict[int, str] = None  # 添加子笔刷字典，存储 {索引: 笔刷名称}

class SystemaxReader:
    """SAI文件读取器"""
    
    def __init__(self):
        self.sai_path: Optional[Path] = None
        self.nrm_path: Optional[Path] = None
        self.saitset_path: Optional[Path] = None
        self.config = ConfigManager()  # 添加配置管理器
        self.folder_path: Optional[str] = None
        self._base_path: Optional[str] = None
        # 添加形状和纹理的基础路径
        self._brushfom_paths = {
            1: "SAIv2/settings/brushfom/blotmap",
            2: "SAIv2/settings/brushfom/bristle",
            3: "SAIv2/settings/brushfom/brshape",
            4: "SAIv2/settings/scatter"
        }
        self._brushtex_path = "SAIv2/settings/brushtex"
        self.brushes: List[BrushData] = []
    
    def initialize(self) -> bool:
        """初始化读取器"""
        # 从配置中获取SAI路径
        saved_path = self.config.get_sai_path()
        
        if saved_path:
            self.sai_path = Path(saved_path)
        else:
            # 如果没有保存的路径，返回False
            print("未设置SAI路径")
            return False
            
        self.nrm_path = self.sai_path / "SAIv2" / "settings" / "custool" / "nrm"
        self.saitset_path = self.nrm_path / "_0.saitset"
        
        if not self.nrm_path.exists():
            print(f"错误：找不到目录 {self.nrm_path}")
            return False
            
        if not self.saitset_path.exists():
            print(f"错误：找不到文件 {self.saitset_path}")
            return False
            
        return True
    
    def _read_file_with_encodings(self, file_path: str) -> Optional[List[str]]:
        """
        使用多种编码尝试读取文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[List[str]]: 文件行列表，读取失败返回None
        """
        encodings = ['utf-8', 'shift-jis', 'cp932', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.readlines()
            except UnicodeDecodeError:
                continue
        
        print(f"无法读取文件 {file_path}")
        return None
    
    def _read_saitset(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        读取saitset文件内容
        
        Returns:
            Tuple[Optional[np.ndarray], Optional[np.ndarray]]: (values_array, indices_array)
        """
        if not self.saitset_path:
            return None, None
            
        values = []
        indices = []
        reading_values = False
        
        lines = self._read_file_with_encodings(str(self.saitset_path))
        if not lines:
            return None, None
            
        for line in lines:
            line = line.strip()
            if line == '.':
                reading_values = not reading_values
                continue
            if reading_values and line:
                index, value = line.split('=')
                indices.append(int(index))
                values.append(int(value))
        
        return np.array(values), np.array(indices)
    
    def _read_saitink(self, ink_value: int, grp_value: int) -> Optional[int]:
        """
        读取.saitlnk文件中的目标笔刷ID
        
        Args:
            ink_value: saitlnk文件编号
            grp_value: 当前正在处理的saitgrp文件编号（用于错误追踪）
            
        Returns:
            Optional[int]: 目标笔刷ID，读取失败返回None
        """
        ink_file = os.path.join(self._base_path, f"{ink_value}.saitlnk")
        try:
            lines = self._read_file_with_encodings(ink_file)
            if not lines:
                print(f"警告: 在处理 _{grp_value}.saitgrp 时无法读取 {ink_value}.saitlnk")
                return None
                
            for line in lines:
                line = line.strip()
                if line.startswith('tarid=I:'):
                    return int(line.split('I:')[1])
            return None
        except FileNotFoundError:
            print(f"警告: 在处理 _{grp_value}.saitgrp 时找不到文件 {ink_value}.saitlnk")
            return None
        except Exception as e:
            print(f"错误: 处理文件 {ink_value}.saitlnk 时发生异常: {str(e)}")
            return None

    def _read_saitdat(self, dat_value: int, grp_value: int) -> Optional[str]:
        """
        读取.saitdat文件中的笔刷名称，如果找不到则尝试通过.saitlnk获取
        
        Args:
            dat_value: saitdat文件编号
            grp_value: 当前正在处理的saitgrp文件编号（用于错误追踪）
            
        Returns:
            Optional[str]: 笔刷名称，读取失败返回None
        """
        dat_file = os.path.join(self._base_path, f"{dat_value}.saitdat")
        try:
            lines = self._read_file_with_encodings(dat_file)
            if lines:
                for line in lines:
                    line = line.strip()
                    if line.startswith('name=U:'):
                        return line.split('U:')[1]
            
            # 如果找不到.saitdat文件或没有找到名称，尝试读取.saitlnk
            target_id = self._read_saitink(dat_value, grp_value)
            if target_id is not None:
                # 递归调用自身来读取目标.saitdat文件
                return self._read_saitdat(target_id, grp_value)
            
            print(f"警告: 在处理 _{grp_value}.saitgrp 时无法读取 {dat_value}.saitdat 或其链接文件")
            return None
            
        except FileNotFoundError:
            # 如果找不到.saitdat，尝试读取.saitlnk
            target_id = self._read_saitink(dat_value, grp_value)
            if target_id is not None:
                # 递归调用自身来读取目标.saitdat文件
                return self._read_saitdat(target_id, grp_value)
            
            print(f"警告: 在处理 _{grp_value}.saitgrp 时找不到文件 {dat_value}.saitdat 或其链接文件")
            return None
        except Exception as e:
            print(f"错误: 处理文件 {dat_value}.saitdat 时发生异常: {str(e)}")
            return None
    
    def _read_brush_data(self, value: int) -> Optional[BrushData]:
        """
        读取单个笔刷组数据
        
        Args:
            value: 笔刷文件编号
            
        Returns:
            Optional[BrushData]: 笔刷数据对象
        """
        grp_file = os.path.join(self._base_path, f"_{value}.saitgrp")
        try:
            lines = self._read_file_with_encodings(grp_file)
            if not lines:
                print(f"错误: 无法读取笔刷组文件 _{value}.saitgrp")
                return None
                
            # 读取笔刷组名称
            brush_name = None
            values = []
            indices = []
            sub_brushes = {}
            reading_values = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('name=U:'):
                    brush_name = line.split('U:')[1]
                elif line == '.':
                    reading_values = not reading_values
                    continue
                elif reading_values and line:
                    index, dat_value = line.split('=')
                    index = int(index)
                    dat_value = int(dat_value)
                    indices.append(index)
                    values.append(dat_value)
                    
                    # 读取对应的.saitdat文件中的笔刷名称
                    sub_brush_name = self._read_saitdat(dat_value, value)  # 传入当前grp文件编号
                    if sub_brush_name:
                        sub_brushes[index] = sub_brush_name
            
            if not brush_name:
                print(f"错误: 在文件 _{value}.saitgrp 中找不到笔刷组名称")
                return None
            
            return BrushData(
                name=brush_name,
                values=np.array(values),
                indices=np.array(indices),
                sub_brushes=sub_brushes
            )
        except Exception as e:
            print(f"错误: 处理文件 _{value}.saitgrp 时发生异常: {str(e)}")
            return None
    
    def read_all_brushes(self) -> List[BrushData]:
        """
        读取所有笔刷数据
        
        Returns:
            List[BrushData]: 笔刷数据列表
        """
        if not self.initialize():
            return []
            
        values_array, _ = self._read_saitset()
        if values_array is None:
            return []
            
        self.brushes = []
        for value in values_array:
            brush_data = self._read_brush_data(value)
            if brush_data:
                self.brushes.append(brush_data)
        
        return self.brushes

    def generate_text_structure(self) -> str:
        """
        生成笔刷结构的文本表示
        
        Returns:
            str: 格式化的笔刷结构文本
        """
        if not self.brushes:
            return "没有找到笔刷数据"
            
        output = []
        output.append("笔刷结构:")
        output.append("=" * 50)
        
        for i, brush in enumerate(self.brushes, 1):
            # 添加笔刷组信息
            output.append(f"\n【笔刷组 {i}】{brush.name}")
            output.append("├─基本信息:")
            output.append(f"│  ├─包含笔刷数量: {len(brush.values)}")
            output.append(f"│  └─索引数量: {len(brush.indices)}")
            
            # 添加子笔刷信息
            output.append("└─子笔刷列表:")
            for idx, sub_name in sorted(brush.sub_brushes.items()):
                output.append(f"   ├─[{idx}] {sub_name}")
            
            # 替换最后一个项目的符号
            if brush.sub_brushes:
                output[-1] = output[-1].replace("├", "└")
            
            output.append("-" * 50)
        
        return "\n".join(output)

    def _export_related_files(self, file_id: int, export_dir: Path, files_copied: set, dat_mapping: dict) -> None:
        """
        导出与指定ID相关的所有文件，包括链接文件，并维护文件映射关系
        
        Args:
            file_id: 文件ID
            export_dir: 导出目录
            files_copied: 已复制文件的集合（避免重复复制）
            dat_mapping: 原始ID到新ID的映射字典
        """
        # 如果文件已经处理过，直接返回
        if file_id in dat_mapping:
            return
        
        # 处理 .saitdat 文件
        dat_file = Path(self._base_path) / f"{file_id}.saitdat"
        if dat_file.exists() and str(dat_file) not in files_copied:
            # 分配新的ID
            new_id = max(dat_mapping.values(), default=0) + 1
            dat_mapping[file_id] = new_id
            
            # 使用新ID复制文件
            new_dat_file = export_dir / f"{new_id}.saitdat"
            shutil.copy2(dat_file, new_dat_file)
            files_copied.add(str(dat_file))
            print(f"已导出: {dat_file.name} -> {new_dat_file.name}")
            return
        
        # 处理 .saitlnk 文件
        lnk_file = Path(self._base_path) / f"{file_id}.saitlnk"
        if lnk_file.exists() and str(lnk_file) not in files_copied:
            try:
                # 读取链接文件内容
                lines = self._read_file_with_encodings(str(lnk_file))
                if lines:
                    for line in lines:
                        if line.strip().startswith('tarid=I:'):
                            target_id = int(line.strip().split('I:')[1])
                            # 递归导出目标文件
                            self._export_related_files(target_id, export_dir, files_copied, dat_mapping)
                            break
            except Exception as e:
                print(f"处理链接文件 {lnk_file.name} 时发生错误: {str(e)}")

    def _update_grp_content(self, grp_content: str, dat_mapping: dict) -> str:
        """
        更新grp文件内容，使用新的dat文件映射
        
        Args:
            grp_content: 原始grp文件内容
            dat_mapping: 原始ID到新ID的映射字典
            
        Returns:
            str: 更新后的grp文件内容
        """
        lines = grp_content.splitlines()
        updated_lines = []
        in_brush_section = False
        current_brush = None
        
        for line in lines:
            if line == '.':
                in_brush_section = not in_brush_section
                updated_lines.append(line)
                continue
            
            if in_brush_section and line.startswith('dataid='):
                # 更新dataid
                old_id = int(line.split('=')[1])
                if old_id in dat_mapping:
                    line = f"dataid={dat_mapping[old_id]}"
            
            updated_lines.append(line)
        
        return '\n'.join(updated_lines)

    def get_brush_group_info(self, group_number: int) -> Optional[dict]:
        """
        获取笔刷组信息,包括实际使用的dat文件编号(处理链接关系)
        
        Args:
            group_number: 笔刷组序号
            
        Returns:
            Optional[dict]: 包含笔刷组信息的字典
        """
        try:
            grp_path = Path(self._base_path) / f"_{group_number}.saitgrp"
            if not grp_path.exists():
                return None
            
            # 读取grp文件内容
            content = grp_path.read_text(encoding='utf-8')
            dat_numbers = []
            reading_values = False
            
            # 解析grp文件,获取所有dat编号
            for line in content.splitlines():
                line = line.strip()
                if line == '.':
                    reading_values = not reading_values
                    continue
                if reading_values and line:
                    _, dat_value = line.split('=')
                    dat_numbers.append(int(dat_value))
            
            # 处理链接关系,获取实际的dat文件编号
            actual_dat_numbers = []
            for dat_number in dat_numbers:
                lnk_path = Path(self._base_path) / f"{dat_number}.saitlnk"
                if lnk_path.exists():
                    # 如果是链接文件,读取目标dat编号
                    lnk_content = lnk_path.read_text(encoding='utf-8')
                    for line in lnk_content.splitlines():
                        if line.startswith('tarid=I:'):
                            target_id = int(line.split('I:')[1])
                            actual_dat_numbers.append(target_id)
                            break
                else:
                    # 如果不是链接文件,直接使用原始编号
                    actual_dat_numbers.append(dat_number)
            
            return {
                'grp_path': grp_path,
                'dat_numbers': actual_dat_numbers  # 返回实际的dat文件编号列表
            }
            
        except Exception as e:
            print(f"获取笔刷组信息时出错: {str(e)}")
            return None

    def export_brush_group(self, group_number: int) -> bool:
        """导出笔刷组"""
        try:
            # 获取exe所在目录
            if getattr(sys, 'frozen', False):
                exe_dir = Path(os.path.dirname(sys.executable))
            else:
                exe_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            
            # 创建导出目录
            export_dir = exe_dir / "exported_brushes"
            export_dir.mkdir(exist_ok=True)
            
            # 获取笔刷组信息
            group_info = self.get_brush_group_info(group_number)
            if not group_info:
                print(f"找不到笔刷组 {group_number}")
                return False
                
            # 创建笔刷组专属目录
            group_dir = export_dir / f"brush_group_{group_number}"
            group_dir.mkdir(exist_ok=True)
            
            # 读取grp文件内容
            grp_content = group_info['grp_path'].read_text(encoding='utf-8')
            
            # 解析grp文件内容
            new_content = []
            actual_dats = set()  # 需要复制的实际dat文件集合
            
            lines = grp_content.splitlines()
            for line in lines:
                line = line.strip()
                if line == '.':
                    new_content.append(line)
                    continue
                
                if '=' in line:
                    index, dat_value = line.split('=')
                    original_dat = int(dat_value)
                    
                    # 检查是否存在链接文件
                    lnk_path = Path(self.nrm_path) / f"{original_dat}.saitlnk"
                    if lnk_path.exists():
                        try:
                            lnk_content = lnk_path.read_text(encoding='utf-8')
                            for lnk_line in lnk_content.splitlines():
                                if lnk_line.startswith('tarid=I:'):
                                    # 获取实际的dat编号
                                    actual_dat = int(lnk_line.split('I:')[1])
                                    # 使用实际的dat编号替换原始编号
                                    new_content.append(f"{index}={actual_dat}")
                                    actual_dats.add(actual_dat)
                                    print(f"替换映射: {index}={original_dat} -> {index}={actual_dat}")
                                    break
                        except Exception as e:
                            print(f"读取链接文件出错 {lnk_path}: {e}")
                            new_content.append(line)
                            actual_dats.add(original_dat)
                    else:
                        new_content.append(line)
                        actual_dats.add(original_dat)
            
            # 写入新的grp文件
            grp_dest = group_dir / group_info['grp_path'].name
            grp_dest.write_text('\n'.join(new_content), encoding='utf-8')
            print(f"已更新并保存笔刷组文件: {grp_dest.name}")
            
            # 复制实际的dat文件
            for actual_dat in actual_dats:
                dat_path = Path(self.nrm_path) / f"{actual_dat}.saitdat"
                if dat_path.exists():
                    shutil.copy2(dat_path, group_dir / dat_path.name)
                    print(f"已复制笔刷文件: {dat_path.name}")
            
            # 复制资源文件
            resource_files = self.get_brush_resource_files(group_number)
            for path, files in resource_files.items():
                if files:
                    # 创建资源类型目录
                    resource_dir = group_dir / path
                    resource_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 复制文件
                    for file in files:
                        src = self.sai_path / "SAIv2" / "settings" / path / file
                        if src.exists():
                            shutil.copy2(src, resource_dir / file)
                            print(f"已复制资源文件: {file} 到 {path}")
            
            print(f"笔刷组 {group_number} 已导出到 {group_dir}")
            return True
            
        except Exception as e:
            print(f"导出笔刷组失败: {e}")
            return False

    def _copy_brush_resource(self, source_dir: Path, target_dir: Path, resource_name: str, extensions: List[str]) -> None:
        """
        复制笔刷资源文件（形状或纹理）
        
        Args:
            source_dir: 源目录
            target_dir: 目标目录
            resource_name: 资源名称
            extensions: 需要复制的文件扩展名列表
        """
        for ext in extensions:
            source_file = source_dir / f"{resource_name}{ext}"
            if source_file.exists():
                shutil.copy2(source_file, target_dir)
                print(f"已导出资源: {source_file.name}")
            else:
                print(f"警告: 找不到资源文件 {source_file}")

    def _update_dat_references(self, grp_content: str, old_to_new: Dict[int, int]) -> str:
        """
        更新.saitgrp文件中的dat引用，保持原有格式
        
        Args:
            grp_content: 原始文件内容
            old_to_new: 旧序号到新序号的映射
            
        Returns:
            str: 更新后的文件内容
        """
        lines = grp_content.splitlines()
        updated_lines = []
        in_values_section = False
        
        for line in lines:
            line = line.rstrip()  # 只移除尾部空白
            if line == '.':
                in_values_section = not in_values_section
                updated_lines.append(line)
                continue
                
            if in_values_section and '=' in line:
                index, old_value = line.split('=')
                old_value = int(old_value)
                if old_value in old_to_new:
                    updated_lines.append(f"{index}={old_to_new[old_value]}")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
                
        # 确保只有一个换行符在文件末尾
        return '\n'.join(updated_lines).rstrip() + '\n'

    def delete_brush_group(self, group_number: int) -> bool:
        """
        删除指定的笔刷组
        
        Args:
            group_number: 笔刷组序号
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 获取笔刷组信息
            group_info = self.get_brush_group_info(group_number)
            if not group_info:
                print(f"找不到笔刷组 {group_number}")
                return False
            
            # 删除关联的dat文件
            for dat_number in group_info['dat_numbers']:
                dat_path = Path(self._base_path) / f"{dat_number}.saitdat"
                if dat_path.exists():
                    dat_path.unlink()
                    print(f"已删除: {dat_path.name}")
            
            # 删除grp文件
            group_info['grp_path'].unlink()
            print(f"已删除: {group_info['grp_path'].name}")
            
            # 更新saitset文件
            saitset_path = Path(self.saitset_path)
            with open(saitset_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 找到并删除对应的索引行
            new_lines = []
            in_index_section = False
            for line in lines:
                if line.strip() == '.':
                    in_index_section = not in_index_section
                    new_lines.append(line)
                    continue
                
                if in_index_section:
                    if '=' in line:
                        index, value = line.strip().split('=')
                        if int(value) != group_number:
                            new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # 写回文件
            with open(saitset_path, 'w', encoding='utf-8', newline='\n') as f:
                f.writelines(new_lines)
            
            print("笔刷组删除成功")
            return True
            
        except Exception as e:
            print(f"删除笔刷组时出错: {str(e)}")
            return False

    def get_brush_resource_files(self, group_number: int) -> dict:
        """
        获取笔刷组使用的资源文件
        
        Args:
            group_number: 笔刷组序号
            
        Returns:
            dict: 资源文件信息 {目录: [文件列表]}
        """
        try:
            group_info = self.get_brush_group_info(group_number)
            if not group_info:
                return {}
            
            resources = {
                'brushfom/blotmap': set(),
                'brushfom/bristle': set(),
                'brushfom/brshape': set(),
                'brushtex': set(),
                'scatter': set()
            }
            
            # 记录已处理的dat文件,避免重复处理
            processed_dats = set()
            
            # 从笔刷文件中读取资源引用
            for dat_number in group_info['dat_numbers']:
                if dat_number in processed_dats:
                    continue
                
                processed_dats.add(dat_number)
                dat_path = Path(self._base_path) / f"{dat_number}.saitdat"
                
                # 检查是否存在链接文件
                lnk_path = Path(self._base_path) / f"{dat_number}.saitlnk"
                if lnk_path.exists():
                    try:
                        lnk_content = lnk_path.read_text(encoding='utf-8')
                        for line in lnk_content.splitlines():
                            if line.startswith('tarid=I:'):
                                target_id = int(line.split('I:')[1])
                                if target_id not in processed_dats:
                                    processed_dats.add(target_id)
                                    # 使用目标dat文件
                                    dat_path = Path(self._base_path) / f"{target_id}.saitdat"
                                break
                    except Exception as e:
                        print(f"读取链接文件时出错: {str(e)}")
                
                # 读取dat文件内容
                if dat_path.exists():
                    try:
                        content = dat_path.read_text(encoding='utf-8')
                        fom_category = None
                        fom_name = None
                        tex_category = None
                        tex_name = None
                        
                        for line in content.splitlines():
                            if line.startswith('fomcat=I:'):
                                fom_category = int(line.split('I:')[1])
                            elif line.startswith('fomnam=U:'):
                                fom_name = line.split('U:')[1]
                            elif line.startswith('texcat=I:'):
                                tex_category = int(line.split('I:')[1])
                            elif line.startswith('texnam=U:'):
                                tex_name = line.split('U:')[1]
                        
                        # 根据fomcat和texcat添加资源文件
                        if fom_name:
                            if fom_category == 1:
                                resources['brushfom/blotmap'].add(f"{fom_name}.bmp")
                            elif fom_category == 2:
                                resources['brushfom/bristle'].add(f"{fom_name}.bmp")
                                resources['brushfom/bristle'].add(f"{fom_name}.ini")
                            elif fom_category == 3:
                                resources['brushfom/brshape'].add(f"{fom_name}.bmp")
                                resources['brushfom/brshape'].add(f"{fom_name}.ini")
                            elif fom_category == 4:
                                resources['scatter'].add(f"{fom_name}.bmp")
                                resources['scatter'].add(f"{fom_name}.ini")
                        
                        if tex_category == 1 and tex_name:
                            resources['brushtex'].add(f"{tex_name}.bmp")
                            
                    except Exception as e:
                        print(f"读取资源文件时出错: {str(e)}")
            
            return resources
            
        except Exception as e:
            print(f"获取资源文件列表时出错: {str(e)}")
            return {}

    def delete_brush_resources(self, resource_files: dict) -> bool:
        """
        删除笔刷相关的资源文件
        
        Args:
            resource_files: 资源文件信息字典
            
        Returns:
            bool: 删除是否成功
        """
        try:
            base_path = Path(self.folder_path)
            deleted_files = []
            
            for rel_path, files in resource_files.items():
                full_path = base_path / "SAIv2" / "settings" / rel_path
                if not full_path.exists():
                    continue
                    
                for filename in files:
                    file_path = full_path / filename
                    if file_path.exists():
                        file_path.unlink()
                        deleted_files.append(str(file_path.relative_to(base_path)))
            
            if deleted_files:
                print("已删除以下资源文件:")
                for file in deleted_files:
                    print(f"- {file}")
            
            return True
            
        except Exception as e:
            print(f"删除资源文件时出错: {str(e)}")
            return False

class BrushImporter:
    """SAI笔刷导入器"""
    
    def __init__(self):
        self.import_path: Optional[Path] = None
        self.sai_path: Optional[Path] = None
        self.nrm_path: Optional[Path] = None
        self.brush_data: Optional[BrushData] = None
        self.saitset_path: Optional[Path] = None
        self.config = ConfigManager()
    
    def initialize(self, select_import_folder: bool = False) -> bool:
        """初始化导入器
        
        Args:
            select_import_folder (bool, optional): 是否选择导入文件夹. Defaults to False.
        """
        try:
            # 从配置中获取SAI路径
            saved_path = self.config.get_sai_path()
            
            if saved_path:
                self.sai_path = Path(saved_path)
            else:
                print("未设置SAI路径")
                return False
                
            self.nrm_path = self.sai_path / "SAIv2" / "settings" / "custool" / "nrm"
            self.saitset_path = self.nrm_path / "_0.saitset"
            
            if not self.nrm_path.exists():
                print(f"错误：找不到目录 {self.nrm_path}")
                return False
                
            if not self.saitset_path.exists():
                print(f"错误：找不到文件 {self.saitset_path}")
                return False

            return True
            
        except Exception as e:
            print(f"初始化失败: {e}")
            return False

    def _get_unused_grp_number(self) -> int:
        """
        获取未使用的最小grp序列号
        """
        used_numbers = set()
        for file in self.nrm_path.glob("_*.saitgrp"):
            try:
                num = int(file.stem.lstrip('_'))
                used_numbers.add(num)
            except ValueError:
                continue
        
        # 寻找未使用的最小序列号
        for num in range(1000):
            if num not in used_numbers:
                return num
        
        raise ValueError("没有可用的序列号")

    def _update_saitset(self, new_grp_number: int) -> bool:
        """
        更新_0.saitset文件，添加新的笔刷组引用
        
        Args:
            new_grp_number: 新的笔刷组序号
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 读取现有内容
            with open(self.saitset_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分割文件内容
            parts = content.split('.')
            if len(parts) != 3:
                print("错误：saitset文件格式不正确")
                return False
            
            # 解析头部、索引部分和尾部
            header = parts[0].strip()
            indices = parts[1].strip()
            footer = parts[2].strip()
            
            # 处理索引部分
            index_lines = [line.strip() for line in indices.split('\n') if line.strip()]
            last_index = -1
            
            # 找到最后一个索引
            for line in index_lines:
                if '=' in line:
                    index = int(line.split('=')[0])
                    last_index = max(last_index, index)
            
            # 添加新的索引
            new_index = last_index + 1
            index_lines.append(f"{new_index}={new_grp_number}")
            
            # 重建文件内容，保持原有格式
            new_content = (
                f"{header}\n"
                f".\n"
                f"{chr(10).join(index_lines)}\n"
                f".\n"
                f"{footer}"
            )
            
            # 写回文件
            with open(self.saitset_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"已更新 _0.saitset: 添加了 {new_index}={new_grp_number}")
            return True
            
        except Exception as e:
            print(f"更新 _0.saitset 时发生错误: {str(e)}")
            return False

    def _get_highest_dat_number(self) -> int:
        """
        获取nrm目录下.saitdat文件的最高序号
        
        Returns:
            int: 最高序号
        """
        highest_num = -1
        for file in self.nrm_path.glob("*.saitdat"):
            try:
                num = int(file.stem)
                highest_num = max(highest_num, num)
            except ValueError:
                continue
        return highest_num

    def _update_dat_references(self, grp_content: str, old_to_new: Dict[int, int]) -> str:
        """
        更新.saitgrp文件中的dat引用，保持原有格式
        
        Args:
            grp_content: 原始文件内容
            old_to_new: 旧序号到新序号的映射
            
        Returns:
            str: 更新后的文件内容
        """
        lines = grp_content.splitlines()
        updated_lines = []
        in_values_section = False
        
        for line in lines:
            line = line.rstrip()  # 只移除尾部空白
            if line == '.':
                in_values_section = not in_values_section
                updated_lines.append(line)
                continue
                
            if in_values_section and '=' in line:
                index, old_value = line.split('=')
                old_value = int(old_value)
                if old_value in old_to_new:
                    updated_lines.append(f"{index}={old_to_new[old_value]}")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
                
        # 确保只有一个换行符在文件末尾
        return '\n'.join(updated_lines).rstrip() + '\n'

    def import_brushes(self) -> bool:
        """执行笔刷导入过程"""
        try:
            # 获取未使用的最小序列号
            new_grp_number = self._get_unused_grp_number()
            print(f"新笔刷组将使用序号: {new_grp_number}")
            
            # 2. 获取dat文件最高序号并处理dat文件
            highest_dat = self._get_highest_dat_number()
            if highest_dat < 0:
                print("错误：无法确定当前最高dat序号")
                return False
            
            next_dat = highest_dat + 1
            
            # 3. 收集并处理文件
            dat_files = list(self.import_path.glob("*.saitdat"))
            grp_files = list(self.import_path.glob("*.saitgrp"))
            
            if not dat_files or not grp_files:
                print("错误：找不到必要的文件")
                return False
            
            # 4. 创建序号映射和处理链接文件
            old_to_new = {}
            processed_dats = set()  # 记录已处理的dat文件
            
            # 首先处理直接的dat文件
            for dat_file in dat_files:
                old_num = int(dat_file.stem)
                old_to_new[old_num] = next_dat
                next_dat += 1
                processed_dats.add(old_num)
            
            # 处理链接文件
            for dat_file in dat_files:
                old_num = int(dat_file.stem)
                lnk_file = self.import_path / f"{old_num}.saitlnk"
                
                if lnk_file.exists():
                    try:
                        # 读取链接文件内容
                        content = lnk_file.read_text(encoding='utf-8')
                        for line in content.splitlines():
                            if line.startswith('tarid=I:'):
                                target_id = int(line.split('I:')[1])
                                target_dat = self.import_path / f"{target_id}.saitdat"
                                
                                # 如果目标文件存在且尚未处理
                                if target_dat.exists() and target_id not in processed_dats:
                                    # 分配新的ID并更新映射
                                    old_to_new[target_id] = next_dat
                                    next_dat += 1
                                    processed_dats.add(target_id)
                                break
                    except Exception as e:
                        print(f"处理链接文件 {lnk_file} 时出错: {str(e)}")
            
            # 5. 复制并重命名文件
            for old_id in processed_dats:
                dat_file = self.import_path / f"{old_id}.saitdat"
                new_id = old_to_new[old_id]
                new_path = self.nrm_path / f"{new_id}.saitdat"
                
                # 复制dat文件
                shutil.copy2(dat_file, new_path)
                print(f"已复制: {dat_file.name} -> {new_path.name}")
                
                # 复制对应的lnk文件(如果存在)
                lnk_file = self.import_path / f"{old_id}.saitlnk"
                if lnk_file.exists():
                    new_lnk_path = self.nrm_path / f"{new_id}.saitlnk"
                    # 读取并更新链接文件内容
                    content = lnk_file.read_text(encoding='utf-8')
                    updated_content = []
                    for line in content.splitlines():
                        if line.startswith('tarid=I:'):
                            target_id = int(line.split('I:')[1])
                            if target_id in old_to_new:
                                line = f"tarid=I:{old_to_new[target_id]}"
                        updated_content.append(line)
                    
                    # 写入更新后的链接文件
                    new_lnk_path.write_text('\n'.join(updated_content) + '\n', encoding='utf-8')
                    print(f"已更新并复制: {lnk_file.name} -> {new_lnk_path.name}")
            
            # 6. 更新并复制.saitgrp文件
            for grp_file in grp_files:
                with open(grp_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                updated_content = self._update_dat_references(content, old_to_new)
                
                new_grp_path = self.nrm_path / f"_{new_grp_number}.saitgrp"
                with open(new_grp_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(updated_content)
                print(f"已更新并复制: {grp_file.name} -> {new_grp_path.name}")
            
            # 7. 更新 _0.saitset 文件
            if not self._update_saitset(new_grp_number):
                print("警告：更新 _0.saitset 失败")
                return False

            # 8. 复制相关的资源文件
            print("\n开始复制相关资源文件...")
            self._copy_brush_resources()
            
            print("\n导入完成！")
            print(f"笔刷组已导入为序号: {new_grp_number}")
            print(f"相关的dat文件序号范围: {highest_dat+1} - {next_dat-1}")
            return True
            
        except Exception as e:
            print(f"导入过程中发生错误: {str(e)}")
            return False

    def read_brush_structure(self) -> Optional[BrushData]:
        """
        读取笔刷组结构
        
        Returns:
            Optional[BrushData]: 笔刷数据对象
        """
        if not self.import_path:
            print("错误：尚未初始化导入器")
            return None
            
        # 查找.saitgrp文件
        grp_files = list(self.import_path.glob("*.saitgrp"))
        if not grp_files:
            print("错误：找不到.saitgrp文件")
            return None
            
        grp_file = grp_files[0]  # 使用找到的第一个.saitgrp文件
        print(f"正在读取笔刷组文件: {grp_file}")  # 调试信息
        
        try:
            lines = self._read_file_with_encodings(str(grp_file))
            if not lines:
                print(f"错误: 无法读取笔刷组文件 {grp_file.name}")
                return None
                
            # 读取笔刷组名称
            brush_name = None
            values = []
            indices = []
            sub_brushes = {}
            reading_values = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('name=U:'):
                    brush_name = line.split('U:')[1]
                elif line == '.':
                    reading_values = not reading_values
                    continue
                elif reading_values and line:
                    index, dat_value = line.split('=')
                    index = int(index)
                    dat_value = int(dat_value)
                    indices.append(index)
                    values.append(dat_value)
                    
                    # 读取对应的.saitdat文件中的笔刷名称
                    dat_file = self.import_path / f"{dat_value}.saitdat"
                    if dat_file.exists():
                        sub_brush_name = self._read_saitdat(dat_file)
                        if sub_brush_name:
                            sub_brushes[index] = sub_brush_name
            
            # 如果没有找到名称，使用文件夹名称
            if not brush_name:
                brush_name = self.import_path.name
            
            return BrushData(
                name=brush_name,
                values=np.array(values),
                indices=np.array(indices),
                sub_brushes=sub_brushes
            )
            
        except Exception as e:
            print(f"错误: 处理文件 {grp_file.name} 时发生异常: {str(e)}")
            return None
    
    def generate_text_structure(self) -> str:
        """
        生成笔刷结构的文本表示
        
        Returns:
            str: 格式化的笔刷结构文本
        """
        # 读取并保存笔刷数据
        self.brush_data = self.read_brush_structure()
        
        if not self.brush_data:
            return "没有找到笔刷数据"
            
        output = []
        output.append("导入的笔刷结构:")
        output.append("=" * 50)
        
        # 添加笔刷组信息
        output.append(f"\n【笔刷组】{self.brush_data.name}")
        output.append("├─基本信息:")
        output.append(f"│  ├─包含笔刷数量: {len(self.brush_data.values)}")
        output.append(f"│  └─索引数量: {len(self.brush_data.indices)}")
        
        # 添加子笔刷信息
        output.append("└─子笔刷列表:")
        for idx, sub_name in sorted(self.brush_data.sub_brushes.items()):
            output.append(f"   ├─[{idx}] {sub_name}")
        
        # 替换最后一个项目的符号
        if self.brush_data.sub_brushes:
            output[-1] = output[-1].replace("├", "└")
        
        output.append("-" * 50)
        
        return "\n".join(output)

    def run(self):
        """运行导入工具的主流程"""
        if not self.initialize():
            return
        
        print("\n当前笔刷组结构:")
        structure = self.generate_text_structure()
        print(structure)
        
        if structure == "没有找到笔刷数据":
            return
        
        while True:
            choice = input("\n是否要导入这个笔刷组？(y/n): ").lower()
            if choice == 'y':
                self.import_brushes()
                break
            elif choice == 'n':
                print("已取消导入")
                break
            else:
                print("请输入 y 或 n")

    def _read_file_with_encodings(self, file_path: str) -> Optional[List[str]]:
        """
        使用多种编码尝试读取文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[List[str]]: 文件行列表，读取失败返回None
        """
        encodings = ['utf-8', 'shift-jis', 'cp932', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.readlines()
            except UnicodeDecodeError:
                continue
        
        print(f"无法读取文件 {file_path}")
        return None

    def _read_saitdat(self, dat_file: Path) -> Optional[str]:
        """
        读取.saitdat文件中的笔刷名称
        
        Args:
            dat_file: .saitdat文件路径
            
        Returns:
            Optional[str]: 笔刷名称，读取失败返回None
        """
        try:
            lines = self._read_file_with_encodings(str(dat_file))
            if lines:
                for line in lines:
                    line = line.strip()
                    if line.startswith('name=U:'):
                        return line.split('U:')[1]
            
            print(f"警告: 在文件 {dat_file.name} 中找不到笔刷名称")
            return None
            
        except Exception as e:
            print(f"错误: 处理文件 {dat_file.name} 时发生异常: {str(e)}")
            return None

    def _copy_brush_resources(self) -> None:
        """复制笔刷相关的资源文件（形状、纹理等）到对应目录"""
        if not self.import_path or not self.sai_path:
            return

        # 定义资源目录映射
        resource_paths = {
            'brushfom/blotmap': 'SAIv2/settings/brushfom/blotmap',
            'brushfom/bristle': 'SAIv2/settings/brushfom/bristle',
            'brushfom/brshape': 'SAIv2/settings/brushfom/brshape',
            'scatter': 'SAIv2/settings/scatter',
            'brushtex': 'SAIv2/settings/brushtex'
        }

        # 遍历每个资源目录
        for src_rel_path, dst_rel_path in resource_paths.items():
            src_path = self.import_path / src_rel_path
            dst_path = self.sai_path / dst_rel_path

            if not src_path.exists():
                continue

            print(f"\n检查资源目录: {src_rel_path}")

            try:
                # 确保目标目录存在
                dst_path.mkdir(parents=True, exist_ok=True)

                # 复制目录中的所有文件
                for src_file in src_path.glob('*.*'):
                    dst_file = dst_path / src_file.name

                    if dst_file.exists():
                        print(f"发现同名文件，跳过: {src_file.name}")
                        continue

                    try:
                        shutil.copy2(src_file, dst_file)
                        print(f"已复制: {src_file.name}")
                    except Exception as e:
                        print(f"复制文件 {src_file.name} 时出错: {str(e)}")

            except Exception as e:
                print(f"处理目录 {src_rel_path} 时出错: {str(e)}")

    def _select_brush_folder(self) -> Optional[str]:
        """选择笔刷组文件夹"""
        root = Tk()
        root.withdraw()
        return filedialog.askdirectory(title="请选择要导入的笔刷组文件夹")

# 使用示例
if __name__ == '__main__':
    importer = BrushImporter()
    importer.run()

# fomcat = 0: 不调用形状，不用管
# fomcat = 1: 形状调用路径为：SAIv2\settings\brushfom\blotmap
# fomcat = 2: 形状调用路径为：SAIv2\settings\brushfom\bristle
# fomcat = 3: 形状调用路径为：SAIv2\settings\brushfom\brshape
# fomcat = 4: 形状调用路径为：SAIv2\settings\scatter

# texcat = 0: 不调用纹理，不用管
# texcat = 1: 纹理调用路径为：SAIv2\settings\brushtex

