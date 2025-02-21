import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from read_Systemax import BrushImporter, SystemaxReader
from config_manager import ConfigManager
import os
import shutil
import sys

class SAIBrushTool:
    def __init__(self):
        # 创建主窗口但不显示
        self.root = tk.Tk()
        self.root.title("SAI导入导出工具")  # 设置窗口标题
        self.root.withdraw()
        
        # 显示警告提示窗口
        self._show_warning_message()
        
        # 设置窗口图标
        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(os.path.dirname(sys.executable), 'icon.ico')
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
                
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"设置图标失败: {e}")
        
        # 创建配置管理器
        self.config = ConfigManager()
        
        # 初始化基础路径
        self.sai_path = None
        self.nrm_path = None
        self.saitset_path = None
        
        # 创建导入器和读取器
        self.importer = BrushImporter()
        self.reader = SystemaxReader()
        
        self._create_widgets()
        self._load_saved_path()
        
        # 显示主窗口
        self.root.deiconify()
        
    def _create_widgets(self):
        """创建GUI组件"""
        # SAI路径框架
        path_frame = ttk.LabelFrame(self.root, text="SAI路径", padding=10)
        path_frame.pack(fill='x', padx=10, pady=5)
        
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=70)
        path_entry.pack(side='left', padx=5)
        
        path_btn = ttk.Button(path_frame, text="选择", command=self._select_sai_path)
        path_btn.pack(side='left', padx=5)
        
        # 创建选项卡
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 导入选项卡
        import_frame = ttk.Frame(notebook, padding=10)
        notebook.add(import_frame, text='导入笔刷')
        self._create_import_tab(import_frame)
        
        # 导出选项卡
        export_frame = ttk.Frame(notebook, padding=10)
        notebook.add(export_frame, text='导出笔刷')
        self._create_export_tab(export_frame)
        
        # README选项卡
        readme_frame = ttk.Frame(notebook, padding=10)
        notebook.add(readme_frame, text='README')
        self._create_readme_tab(readme_frame)
        
        # 状态标签
        self.status_var = tk.StringVar()
        status_label = ttk.Label(self.root, textvariable=self.status_var)
        status_label.pack(pady=5)
        
    def _create_import_tab(self, parent):
        """创建导入选项卡的内容"""
        # 笔刷组框架
        brush_frame = ttk.LabelFrame(parent, text="笔刷组", padding=10)
        brush_frame.pack(fill='x', pady=5)
        
        self.brush_path_var = tk.StringVar()
        brush_entry = ttk.Entry(brush_frame, textvariable=self.brush_path_var, width=50)
        brush_entry.pack(side='left', padx=5)
        
        brush_btn = ttk.Button(brush_frame, text="选择", command=self._select_brush_folder)
        brush_btn.pack(side='left', padx=5)
        
        # 结构显示框架
        structure_frame = ttk.LabelFrame(parent, text="笔刷组结构", padding=10)
        structure_frame.pack(fill='both', expand=True, pady=5)
        
        # 使用Text组件显示结构
        self.import_text = tk.Text(structure_frame, wrap='word', height=15)
        self.import_text.pack(fill='both', expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(structure_frame, orient='vertical', command=self.import_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.import_text.configure(yscrollcommand=scrollbar.set)
        
        # 导入按钮
        self.import_btn = ttk.Button(parent, text="导入笔刷组", command=self._import_brushes)
        self.import_btn.pack(pady=10)
        self.import_btn.state(['disabled'])
        
    def _create_export_tab(self, parent):
        """创建导出选项卡的内容"""
        # 笔刷结构显示框架
        structure_frame = ttk.LabelFrame(parent, text="当前笔刷结构", padding=10)
        structure_frame.pack(fill='both', expand=True, pady=5)
        
        # 工具栏
        toolbar = ttk.Frame(structure_frame)
        toolbar.pack(fill='x', pady=5)
        
        refresh_btn = ttk.Button(toolbar, text="刷新结构", command=self._refresh_structure)
        refresh_btn.pack(side='left', padx=5)
        
        # 笔刷组列表和操作区域
        list_frame = ttk.LabelFrame(parent, text="笔刷组操作", padding=10)
        list_frame.pack(fill='x', pady=5)
        
        # 创建笔刷组列表框
        self.brush_listbox = tk.Listbox(list_frame, selectmode='multiple', height=6)
        self.brush_listbox.pack(side='left', fill='both', expand=True, padx=5)
        
        # 添加滚动条
        listbox_scroll = ttk.Scrollbar(list_frame, orient='vertical', command=self.brush_listbox.yview)
        listbox_scroll.pack(side='right', fill='y')
        self.brush_listbox.configure(yscrollcommand=listbox_scroll.set)
        
        # 按钮框架
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill='x', pady=5)
        
        # 删除按钮
        delete_btn = ttk.Button(button_frame, text="删除选中的笔刷组", command=self._delete_brush_group)
        delete_btn.pack(side='left', padx=5)
        
        # 导出按钮
        export_btn = ttk.Button(button_frame, text="导出选中的笔刷组", command=self._export_selected_brushes)
        export_btn.pack(side='left', padx=5)
        
        # 使用Text组件显示结构
        self.export_text = tk.Text(structure_frame, wrap='word', height=20)
        self.export_text.pack(fill='both', expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(structure_frame, orient='vertical', command=self.export_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.export_text.configure(yscrollcommand=scrollbar.set)
        
    def _create_readme_tab(self, parent):
        """创建README选项卡的内容"""
        # 创建Text组件
        readme_text = tk.Text(parent, wrap='word', height=30)
        readme_text.pack(fill='both', expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=readme_text.yview)
        scrollbar.pack(side='right', fill='y')
        readme_text.configure(yscrollcommand=scrollbar.set)
        
        # README内容
        readme_content = """
SAI笔刷工具使用说明
此软件基于2022.01.05版本的SAI2进行开发
推荐版本至少2020以上。
特别感谢夜月七境的博客，提供了很多思路：https://piv.ink/import-sai-settings/

========================================================================

                            ！！！注意事项！！！

1. 导入/导出前请确保SAI2已关闭
2. 建议在操作前备份SAI2的设置文件夹。尤其是SAIv2/settings/custool/nrm文件夹。
3. 删除笔刷组时请谨慎操作，特别是删除资源文件时要注意是否有其他笔刷组在使用相同的资源

========================================================================

基本功能：
1. 导入/导出SAI2笔刷组
2. 管理现有笔刷组

使用前准备：
1. 选择SAI2安装目录（SYSTEMAX Software Development文件夹）

========================================================================


导出笔刷组：
1. 在"导出笔刷"页面可以看到当前所有笔刷组
2. 可以选择单个或多个笔刷组进行导出
3. 导出的笔刷组会保存在程序目录下的exported_brushes文件夹中
4. 导出时会自动包含所有相关的资源文件（形状、材质等）

导入笔刷组：
1. 在"导入笔刷"页面可以导入此软件导出格式的笔刷组
3. 选择要导入的笔刷组文件夹后会显示笔刷组结构
4. 确认无误后点击"导入笔刷组"即可

删除笔刷组：
1. 在"导出笔刷"页面可以删除现有的笔刷组
2. 可以选择是否同时删除相关的资源文件
3. 删除前会显示详细的文件列表供确认


========================================================================

文件路径说明：
1. SAI2安装目录：SYSTEMAX Software Development
2. 笔刷设置目录：SAIv2/settings/custool/nrm
3. 形状文件目录：SAIv2/settings/brushfom
4. 材质文件目录：SAIv2/settings/brushtex
5. 散布图案目录：SAIv2/settings/scatter
6. 导出文件目录：和exe文件位于同一路经

如有问题或建议，请联系开发者。

阿缅
2025.02.20

"""
        
        # 插入内容
        readme_text.insert('1.0', readme_content)
        # 设置为只读
        readme_text.configure(state='disabled')
        
    def _load_saved_path(self):
        """加载保存的SAI路径"""
        saved_path = self.config.get_sai_path()
        if saved_path and Path(saved_path).exists():
            self._update_sai_path(saved_path)
            self.path_var.set(saved_path)
            
    def _update_sai_path(self, path: str) -> bool:
        """
        更新SAI路径相关的设置
        
        Args:
            path: SAI路径
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 更新基础路径
            self.sai_path = Path(path)
            self.nrm_path = self.sai_path / "SAIv2" / "settings" / "custool" / "nrm"
            self.saitset_path = self.nrm_path / "_0.saitset"
            
            # 验证路径
            if not self.nrm_path.exists() or not self.saitset_path.exists():
                messagebox.showerror("错误", "无效的SAI路径")
                return False
            
            # 更新导入器设置
            self.importer.sai_path = self.sai_path
            self.importer.nrm_path = self.nrm_path
            self.importer.saitset_path = self.saitset_path
            
            # 更新读取器设置
            self.reader.folder_path = str(self.sai_path)
            self.reader.saitset_path = str(self.saitset_path)
            self.reader._base_path = str(self.nrm_path)
            
            # 初始化读取器
            self.reader.initialize()
            self.reader.read_all_brushes()
            
            # 保存路径到配置
            self.config.set_sai_path(str(self.sai_path))
            self.status_var.set("SAI路径已更新")
            
            # 刷新笔刷结构显示
            self._refresh_structure()
            
            return True
            
        except Exception as e:
            print(f"更新SAI路径时发生错误: {str(e)}")
            return False
            
    def _select_sai_path(self):
        """选择SAI路径"""
        from tkinter import filedialog
        path = filedialog.askdirectory(title="请选择SYSTEMAX Software Development文件夹")
        if path:
            if self._update_sai_path(path):
                self.path_var.set(path)
            
    def _select_brush_folder(self):
        """选择笔刷组文件夹"""
        from tkinter import filedialog
        
        # 设置默认目录为exe同目录下的exported_brushes
        exe_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        default_dir = exe_dir / "exported_brushes"
        
        folder = filedialog.askdirectory(
            title="请选择要导入的笔刷组文件夹",
            initialdir=default_dir if default_dir.exists() else None
        )
        
        if folder:
            self.brush_path_var.set(folder)
            self.importer.import_path = Path(folder)
            
            # 检查是否存在.saitgrp文件
            grp_files = list(self.importer.import_path.glob("*.saitgrp"))
            if not grp_files:
                messagebox.showerror("错误", "在选择的文件夹中找不到.saitgrp文件")
                return
                
            # 显示笔刷组结构
            self.import_text.delete('1.0', tk.END)
            structure = self.importer.generate_text_structure()
            self.import_text.insert('1.0', structure)
            
            if structure != "没有找到笔刷数据":
                self.import_btn.state(['!disabled'])
                self.status_var.set("笔刷组已加载")
            else:
                self.import_btn.state(['disabled'])
                self.status_var.set("无法读取笔刷组数据")
                
    def _import_brushes(self):
        """导入笔刷组"""
        if messagebox.askyesno("确认", "是否要导入这个笔刷组？"):
            try:
                if self.importer.import_brushes():
                    messagebox.showinfo("成功", "笔刷组导入成功！")
                    self.status_var.set("导入完成")
                    self._refresh_structure()  # 刷新笔刷结构
                else:
                    messagebox.showerror("错误", "笔刷组导入失败")
                    self.status_var.set("导入失败")
            except Exception as e:
                messagebox.showerror("错误", f"导入过程中发生错误：{str(e)}")
                self.status_var.set("导入出错")
                
    def _refresh_structure(self):
        """刷新笔刷结构显示"""
        try:
            if not self.sai_path or not self.sai_path.exists():
                self.status_var.set("请先选择有效的SAI路径")
                return
                
            self.export_text.delete('1.0', tk.END)
            self.brush_listbox.delete(0, tk.END)  # 清空列表框
            
            # 重新初始化读取器
            self.reader = SystemaxReader()
            self.reader.folder_path = str(self.sai_path)
            self.reader.saitset_path = str(self.saitset_path)
            self.reader._base_path = str(self.nrm_path)
            
            # 初始化并读取所有笔刷
            if self.reader.initialize():
                self.reader.read_all_brushes()
                structure = self.reader.generate_text_structure()
                
                if structure:
                    self.export_text.insert('1.0', structure)
                    self.status_var.set("笔刷结构已刷新")
                    
                    # 更新笔刷组列表
                    for group_number in range(1, 1000):  # 假设最大1000个笔刷组
                        group_info = self.reader.get_brush_group_info(group_number)
                        if group_info:
                            # 读取笔刷组名称
                            grp_content = group_info['grp_path'].read_text(encoding='utf-8')
                            name_line = next((line for line in grp_content.splitlines() if line.startswith('name=')), None)
                            group_name = name_line.split('=')[1] if name_line else f"group_{group_number}"
                            
                            # 移除名称中的"U:"前缀
                            if group_name.startswith("U:"):
                                group_name = group_name[2:]
                            
                            self.brush_listbox.insert(tk.END, f"{group_number}: {group_name}")
                else:
                    self.export_text.insert('1.0', "没有找到笔刷数据")
                    self.status_var.set("无法读取笔刷数据")
            else:
                self.export_text.insert('1.0', "初始化读取器失败")
                self.status_var.set("初始化失败")
            
        except Exception as e:
            error_msg = f"刷新结构时发生错误: {str(e)}"
            print(error_msg)
            self.status_var.set(error_msg)
            self.export_text.insert('1.0', "刷新结构时发生错误")
                
    def _delete_brush_group(self):
        """删除选中的笔刷组"""
        try:
            # 获取选中的项目
            selections = self.brush_listbox.curselection()
            if not selections:
                messagebox.showwarning("警告", "请先选择要删除的笔刷组")
                return
            
            for index in selections:
                # 从列表项文本中提取笔刷组序号
                item_text = self.brush_listbox.get(index)
                group_number = int(item_text.split(':')[0])
                group_name = item_text.split(':', 1)[1].strip()
                
                # 获取笔刷组信息
                group_info = self.reader.get_brush_group_info(group_number)
                if not group_info:
                    messagebox.showerror("错误", f"找不到笔刷组 {group_number}")
                    continue
                
                # 获取相关的资源文件信息
                resource_files = self.reader.get_brush_resource_files(group_number)
                
                # 构建确认消息
                confirm_msg = f"确定要删除笔刷组 {group_number}: {group_name} 吗？\n"
                confirm_msg += f"这将删除以下文件：\n"
                
                # 显示grp文件及其包含的笔刷名称
                grp_content = group_info['grp_path'].read_text(encoding='utf-8')
                brush_names = []
                current_section = None
                
                # 读取每个.saitdat文件的名称
                dat_brush_names = {}
                for dat_number in group_info['dat_numbers']:
                    dat_path = Path(self.nrm_path) / f"{dat_number}.saitdat"
                    if dat_path.exists():
                        try:
                            with open(dat_path, 'r', encoding='utf-8') as f:
                                dat_content = f.read()
                                for line in dat_content.splitlines():
                                    if line.startswith('name='):
                                        name = line.split('=')[1]
                                        if name.startswith('U:'):
                                            name = name[2:]
                                        dat_brush_names[dat_number] = name
                                        break
                        except:
                            dat_brush_names[dat_number] = f"笔刷{dat_number}"
                
                confirm_msg += f"- {group_info['grp_path'].name} (笔刷组：{group_name})\n"
                
                # 显示dat文件及其对应的笔刷名称
                for dat_number in group_info['dat_numbers']:
                    brush_name = dat_brush_names.get(dat_number, f"笔刷{dat_number}")
                    confirm_msg += f"- {dat_number}.saitdat ({brush_name})\n"
                
                # 显示资源文件信息
                has_resources = any(files for files in resource_files.values())
                if has_resources:
                    confirm_msg += "\n该笔刷组关联以下资源文件：\n"
                    for path, files in resource_files.items():
                        if files:
                            # 根据路径显示资源类型
                            resource_type = {
                                'brushfom/blotmap': '形状',
                                'brushfom/bristle': '笔触',
                                'brushfom/brshape': '笔形',
                                'scatter': '散布',
                                'brushtex': '纹理'
                            }.get(path, '其他')
                            
                            for file in files:
                                confirm_msg += f"- {path}/{file} ({resource_type})\n"
            
                if not messagebox.askyesno("确认删除", confirm_msg):
                    continue
            
                # 如果有资源文件，询问是否一并删除
                delete_resources = False
                if has_resources:
                    delete_resources = messagebox.askyesno(
                        "删除资源文件",
                        "是否同时删除相关的材质和形状文件？\n"
                        "注意：如果其他笔刷组也在使用这些文件，删除后可能会影响其他笔刷组的显示。"
                    )
                    
                    # 如果用户选择删除资源文件，进行二次确认
                    if delete_resources:
                        second_confirm = messagebox.askyesno(
                            "！！危险操作确认！！",
                            "【警告】您真的要删除全部相关的形状和材质文件吗？\n\n"
                            "这个操作不可撤销，可能会影响其他笔刷组的显示。\n"
                            "建议您在操作前备份 SAI2 的设置文件夹。",
                            icon='warning'
                        )
                        # 如果用户在二次确认时选择否，则取消删除资源文件
                        if not second_confirm:
                            delete_resources = False
            
                # 执行删除
                if self.reader.delete_brush_group(group_number):
                    # 如果用户确认删除资源文件
                    if delete_resources:
                        self.reader.delete_brush_resources(resource_files)
                        messagebox.showinfo("成功", f"笔刷组 {group_number} 和相关资源文件已删除")
                    else:
                        messagebox.showinfo("成功", f"笔刷组 {group_number} 删除成功")
                else:
                    messagebox.showerror("错误", f"删除笔刷组 {group_number} 失败")
            
            self._refresh_structure()  # 刷新显示
            
        except Exception as e:
            messagebox.showerror("错误", f"删除过程中发生错误：{str(e)}")
                
    def _export_selected_brushes(self):
        """导出选中的笔刷组"""
        try:
            # 获取选中的项目
            selections = self.brush_listbox.curselection()
            if not selections:
                messagebox.showwarning("警告", "请先选择要导出的笔刷组")
                return
            
            # 创建导出基础目录（在exe同目录下）
            if getattr(sys, 'frozen', False):
                exe_dir = Path(os.path.dirname(sys.executable))
            else:
                exe_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            
            export_base_path = exe_dir / "exported_brushes"
            export_base_path.mkdir(exist_ok=True)
            
            # 确保读取器已正确初始化
            if not self.reader.initialize():
                messagebox.showerror("错误", "读取器初始化失败")
                return
            
            # 导出每个选中的笔刷组
            success_count = 0
            failed_groups = []
            
            for index in selections:
                # 从列表项文本中提取笔刷组序号
                item_text = self.brush_listbox.get(index)
                group_number = int(item_text.split(':')[0])
                group_name = item_text.split(':', 1)[1].strip()
                
                try:
                    # 创建该笔刷组的导出目录
                    safe_name = group_name.replace(':', '_').replace('/', '_').replace('\\', '_')
                    export_path = export_base_path / f"group_{group_number}_{safe_name}"
                    export_path.mkdir(parents=True, exist_ok=True)
                    
                    # 获取笔刷组信息
                    group_info = self.reader.get_brush_group_info(group_number)
                    if not group_info:
                        failed_groups.append(group_number)
                        continue
                    
                    # 读取原始grp文件内容
                    grp_file = group_info['grp_path']
                    grp_content = grp_file.read_text(encoding='utf-8')
                    
                    # 解析grp文件内容
                    sections = grp_content.split('.')
                    header_section = []
                    mapping_section = []
                    actual_dats = set()  # 需要复制的实际dat文件集合
                    
                    # 处理头部信息
                    if len(sections) > 1:
                        header_lines = sections[0].strip().splitlines()
                        for line in header_lines:
                            line = line.strip()
                            if line:
                                header_section.append(line)
                    
                    # 处理映射部分
                    mapping_lines = sections[1].strip().splitlines()
                    for line in mapping_lines:
                        line = line.strip()
                        if '=' in line:
                            index, dat_value = line.split('=')
                            try:
                                original_dat = int(dat_value)
                                # 检查是否存在链接文件
                                lnk_path = Path(self.nrm_path) / f"{original_dat}.saitlnk"
                                if lnk_path.exists():
                                    try:
                                        lnk_content = lnk_path.read_text(encoding='utf-8')
                                        for lnk_line in lnk_content.splitlines():
                                            if lnk_line.startswith('tarid='):
                                                _, target_value = lnk_line.split('=', 1)
                                                if target_value.startswith('I:'):
                                                    target_value = target_value[2:]
                                                actual_dat = int(target_value.strip())
                                                mapping_section.append(f"{index}={actual_dat}")
                                                actual_dats.add(actual_dat)
                                                break
                                        else:
                                            mapping_section.append(line)
                                            actual_dats.add(original_dat)
                                    except Exception as e:
                                        print(f"读取链接文件出错 {lnk_path}: {e}")
                                        mapping_section.append(line)
                                        actual_dats.add(original_dat)
                                else:
                                    mapping_section.append(line)
                                    actual_dats.add(original_dat)
                            except ValueError:
                                mapping_section.append(line)
                    
                    # 构建新的grp文件内容
                    new_content = []
                    # 添加头部信息
                    new_content.extend(header_section)
                    new_content.append('.')
                    # 添加映射信息
                    new_content.extend(mapping_section)
                    new_content.append('.')
                    # 添加文件结束标记
                    new_content.append('--EOF--')
                    
                    # 写入新的grp文件
                    new_grp_path = export_path / grp_file.name
                    new_grp_path.write_text('\n'.join(new_content), encoding='utf-8')
                    
                    # 用于存储需要的资源信息
                    needed_resources = {}  # {目录: {文件名}}
                    
                    # 遍历每个dat文件，检查其fomcat和texcat值
                    for dat_number in actual_dats:
                        dat_path = Path(self.nrm_path) / f"{dat_number}.saitdat"
                        if not dat_path.exists():
                            continue
                            
                        try:
                            # 读取dat文件内容
                            dat_content = dat_path.read_text(encoding='utf-8')
                            fomcat = None
                            texcat = None
                            fomnam = None
                            texnam = None
                            
                            # 解析值
                            for line in dat_content.splitlines():
                                line = line.strip()
                                if line.startswith('fomcat='):
                                    value = line.split('=')[1]
                                    if value.startswith('I:'):
                                        fomcat = int(value[2:])
                                elif line.startswith('texcat='):
                                    value = line.split('=')[1]
                                    if value.startswith('I:'):
                                        texcat = int(value[2:])
                                elif line.startswith('fomnam=U:'):
                                    fomnam = line.split('U:')[1]
                                elif line.startswith('texnam=U:'):
                                    texnam = line.split('U:')[1]
                        
                            print(f"笔刷 {dat_number}.saitdat: fomcat={fomcat}, texcat={texcat}")
                            print(f"fomnam={fomnam}, texnam={texnam}")
                            
                            # 根据fomcat和fomnam添加需要的资源
                            if fomcat and fomnam:
                                if fomcat == 1:
                                    needed_resources.setdefault('brushfom/blotmap', set()).add(fomnam)
                                elif fomcat == 2:
                                    needed_resources.setdefault('brushfom/bristle', set()).add(fomnam)
                                elif fomcat == 3:
                                    needed_resources.setdefault('brushfom/brshape', set()).add(fomnam)
                                elif fomcat == 4:
                                    needed_resources.setdefault('scatter', set()).add(fomnam)
                            
                            # 根据texcat和texnam添加需要的资源
                            if texcat == 2 and texnam:
                                needed_resources.setdefault('brushtex', set()).add(texnam)
                            
                        except Exception as e:
                            print(f"处理dat文件 {dat_number} 时出错: {e}")
                    
                    print(f"需要的资源: {needed_resources}")
                    
                    # 复制需要的资源文件
                    for resource_dir, filenames in needed_resources.items():
                        # 创建目标目录
                        target_dir = export_path / resource_dir
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        for filename in filenames:
                            # 确定需要复制的文件扩展名
                            if resource_dir in ['brushfom/blotmap', 'brushfom/bristle', 'brushtex']:
                                extensions = ['.bmp']
                            else:
                                extensions = ['.bmp', '.ini']
                            
                            # 复制文件
                            for ext in extensions:
                                src_path = self.sai_path / "SAIv2/settings" / resource_dir / f"{filename}{ext}"
                                if src_path.exists():
                                    dst_path = target_dir / f"{filename}{ext}"
                                    shutil.copy2(src_path, dst_path)
                                    print(f"已复制资源文件: {filename}{ext} 到 {resource_dir}")
                                else:
                                    print(f"警告: 找不到资源文件 {src_path}")
                    
                    # 复制dat文件
                    for actual_dat in actual_dats:
                        dat_file = Path(self.nrm_path) / f"{actual_dat}.saitdat"
                        if dat_file.exists():
                            shutil.copy2(dat_file, export_path / dat_file.name)
                            print(f"已复制笔刷文件: {dat_file.name}")
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"导出笔刷组 {group_number} 时出错: {str(e)}")
                    failed_groups.append(group_number)
            
            # 显示结果
            if success_count > 0:
                success_msg = f"成功导出 {success_count} 个笔刷组到 exported_brushes 目录"
                if failed_groups:
                    success_msg += f"\n但以下笔刷组导出失败: {', '.join(map(str, failed_groups))}"
                messagebox.showinfo("导出完成", success_msg)
                
                # 打开导出文件夹
                try:
                    os.startfile(str(export_base_path))
                except Exception as e:
                    print(f"打开文件夹失败: {e}")
            else:
                messagebox.showerror("错误", "所有笔刷组导出失败")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出过程中发生错误：{str(e)}")
                
    def _show_warning_message(self):
        """显示警告提示窗口"""
        warning_window = tk.Toplevel()
        warning_window.title("重要提示")
        # 加大第一行的字号
        label_first_line = tk.Label(warning_window, text="本软件只支持SAI2 2020及以后版本", font=("Arial", 12, "bold"))
        label_first_line.pack(pady=(10, 0))
        label_first_line = tk.Label(warning_window, text="第一次使用软件，或者对文件操作没自信？", font=("Arial", 12, "bold"))
        label_first_line.pack(pady=(10, 0))
        # 设置警告信息
        warning_message = (
            "1. 如果你对自己的操作完全没信心，害怕笔刷丢失，请备份：\n"
            "   Documents\\SYSTEMAX Software Development\n\n"
            "2. 如果只是普通担心，想留个备份以防万一，请备份：\n"
            "   SYSTEMAX Software Development\\SAIv2\\settings\\custool\n\n"
            "3. 如果你和我一样神经大条，至少备份：\n"
            "   SYSTEMAX Software Development\\SAIv2\\settings\\custool\\nrm"
        )
        
        # 创建标签并设置字体
        label = tk.Label(warning_window, text=warning_message, justify="left", font=("Arial", 10))
        label.pack(padx=20, pady=20)
        label_first_line = tk.Label(warning_window, text="禁止二次贩卖，此软件永远免费发布", font=("Arial", 12, "bold"))
        label_first_line.pack(pady=(10, 0))
        # 确认按钮
        confirm_button = tk.Button(warning_window, text="确认", command=warning_window.destroy)
        confirm_button.pack(pady=10)
        
        # 等待用户关闭警告窗口
        self.root.wait_window(warning_window)
        
    def run(self):
        """运行GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = SAIBrushTool()
    app.run()