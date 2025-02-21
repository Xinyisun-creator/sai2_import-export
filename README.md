# SAI导入导出工具

## 简介

你好，我是阿缅。

本工具基于 **SAI2 2020 及以后版本** 设计，功能为 **快捷导入与导出笔刷组** 。  

手动调整参数既繁琐又耗时，这款工具正是为了解决这一问题，同时也方便大家 **共享笔刷**。  

特别感谢 **夜月七境** 的博客提供了许多宝贵思路：[链接](https://piv.ink/import-sai-settings/)  

以及感谢信任我、帮助我进行测试的大家。万分感谢。

## 功能

- **导入笔刷组**：从指定目录导入笔刷组。
- **导出笔刷组**：将选定的笔刷组导出到 `exported_brushes` 目录。
- **删除笔刷组**：删除选定的笔刷组，并可选择删除相关资源文件。
- **备份提示**：在软件启动时提供备份建议。

## 使用说明

### 启动软件

1. 双击 `SAI导入导出工具.exe` 启动软件。
2. 启动时会显示备份提示窗口，建议根据提示进行备份。

### 导入笔刷组

1. 点击“导入”按钮。
2. 选择包含笔刷组的目录。
3. 软件会自动选择未使用的最小序列号进行导入。

### 导出笔刷组

1. 在列表中选择要导出的笔刷组。
2. 点击“导出”按钮。
3. 成功导出后，软件会自动打开 `exported_brushes` 目录。

### 删除笔刷组

1. 在列表中选择要删除的笔刷组。
2. 点击“删除”按钮。
3. 确认删除操作，并选择是否删除相关资源文件。

## 注意事项

- **备份建议**：
  - 如果对操作不自信，请备份：`Documents\SYSTEMAX Software Development`
  - 如果只是普通担心，请备份：`SYSTEMAX Software Development\SAIv2\settings\custool`
  - 至少备份：`SYSTEMAX Software Development\SAIv2\settings\custool\nrm`

## 依赖

- Python 3.x
- PyInstaller（用于打包）

## 打包

使用以下命令打包项目：
pyinstaller --onefile --windowed --icon=path/to/icon.ico your_script.py




## 特别提示

禁止将本软件进行二次贩卖。
