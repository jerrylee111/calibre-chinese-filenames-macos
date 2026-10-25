# calibre 中文文件名补丁：macOS 打包参考

将 calibre 9.17.0 书库中的中文作者、书名保留为中文目录和文件名，并制作可独立使用的 macOS 应用。

例如，新增书籍后得到：

```text
刘慈欣/
└── 三体：地球往事 (1)/
    └── 三体：地球往事 - 刘慈欣.txt
```

这是个人补丁与封装方法参考，非 calibre 官方发行版。实现方式是 **同版本官方 macOS 运行库 + 内置补丁源码 + 重新编译的启动程序**，不是从零编译 Python、Qt 等全部依赖。

## 下载与安装

在 [Releases](https://github.com/jerrylee111/calibre-chinese-filenames-macos/releases) 下载：

- `calibre-9.17.0-chinese-macos.dmg`：可安装版本。
- `calibre-9.17.0-chinese-source.tar.gz`：制作初始安装包时使用的完整 calibre 源码和封装脚本。
- `SHA256SUMS.txt`：上述文件的 SHA-256 校验值。

退出 calibre，打开 DMG，将 `calibre.app` 拖入“应用程序”。若想保留官方版本，可先给原应用改名。应用不依赖下载目录里的源码，不需要另装 Python。

要求 macOS 14 或更新版本；包含 arm64 和 x86_64 两种架构。实测环境为 Apple Silicon / macOS 27.0.1，未在 Intel 硬件上实测。

本包使用本地临时签名，未进行 Apple 开发者签名和公证。首次打开可能需要在“系统设置 → 隐私与安全性”中允许打开。通过官方安装包更新会覆盖补丁。

## 修改了什么

### 1. 原始中文文件名补丁

[`patches/chinese-filenames.patch`](patches/chinese-filenames.patch) 在 `src/calibre/db/backend.py` 的两个方法中各注释两行：

```python
#author = ascii_filename(author)[:l]
#title = ascii_filename(title.lstrip())[:l].rstrip()
```

涉及 `construct_path_name()` 和 `construct_file_name()`。这里保留原有四行补丁，不扩展为另一套命名规则。

**边界：**这四行同时承担了字符清理和长度截断。注释后，包含 `/` 等路径分隔符或非常长的作者、书名可能导入失败。因此本仓库更适合作为方法参考；如需进一步维护，应设计保留 Unicode 的字符清理和按文件系统限制截断的方案。

已有的拼音目录不会仅因启动本版本而自动批量改名；新增书籍或更新相关元数据时使用补丁逻辑。

### 2. 应用内源码与启动程序

[`scripts/build_app.py`](scripts/build_app.py) 将源码复制到应用内：

```text
calibre.app/Contents/Resources/ChineseSource/src/
```

随后基于上游 `bypy/macos/launcher.c` 重新编译所有启动入口。每次启动时根据应用的真实位置设置 `CALIBRE_DEVELOP_FROM`，不写死本机路径；子进程也从包内加载源码。

启动前设置 UTF-8 字符环境，解决底层运行库在包含中文的应用路径中找不到 `python-lib.bypy.frozen` 的问题。

### 3. 使用已构建的界面与网页资源

[`patches/packaging-resources.patch`](patches/packaging-resources.patch) 仅用于封装副本：让 `calibre/constants.py` 中的 `is_running_from_develop` 为 `False`。

源码仍由启动器加载，但界面、图标、阅读器和内容服务器使用同版本官方预构建资源，避免启动时要求生成文件，支持从只读安装镜像运行。打包脚本会自动进行此适配。

## 自己打包

准备以下输入，**源码和官方应用都必须为 9.17.0**：

1. macOS 和 Apple Command Line Tools（提供 `clang`、`codesign` 等）。
2. Python 3.11 或更新版本，用于运行本仓库的封装脚本。
3. [calibre 官方源码](https://download.calibre-ebook.com/9.17.0/) 和[同版本 macOS 安装包](https://download.calibre-ebook.com/9.17.0/)。
4. 将官方 DMG 挂载，找到其中的 `calibre.app`。

在仓库目录执行，替换为自己的绝对路径：

```sh
python3 scripts/package_macos.py \
  --source /path/to/calibre-9.17.0 \
  --base-app /Volumes/calibre-9.17.0/calibre.app \
  --output /path/to/dist/calibre-9.17.0-chinese-macos.dmg
```

`--source` 可以是未修改的官方源码，也可以是已经应用上述四行补丁的源码。脚本会复制所需内容，在临时目录应用补丁、构建、签名和制作镜像；不修改输入源码或官方应用，不覆盖已有输出文件。

中间构建位于系统临时目录。不要直接在 iCloud 同步的 Documents 目录中签名应用：文件提供程序可能重新附加 `FinderInfo` 属性，导致签名失败。

封装方式依赖 calibre 9.17.0 的启动 ABI 和目录结构。升级版本时需要重新核对，不能只替换版本号。

## 验证

[初始发行版验证记录](docs/validation-9.17.0.txt) 包含中文导入、修改书名和作者、文件内容完整性、TXT 转 EPUB、GUI 启动与正常退出、中文及空格路径、只读 DMG 运行和签名检查。

[验证操作说明](docs/testing.md) 提供独立测试书库的复现步骤。测试不会操作个人日常书库。

## 目录

```text
patches/                   原始中文补丁、资源模式适配补丁
scripts/package_macos.py   从源码与官方 app 制作 DMG
scripts/build_app.py       内置源码、重编译启动器、本地签名
scripts/check_chinese.py   中文导入与改名验证
scripts/check_gui.py       隔离配置下的 GUI 冒烟验证
```

安装包和完整源码放在 Releases 中，避免将大文件提交到 Git 历史。本仓库不包含个人书库、配置、账号凭据或本机运行日志。

## 来源与许可证

- 最初思路参考用户提供的 [Windows 旧版教程](https://zhuanlan.zhihu.com/p/245553023)。本文记录的是 calibre 9.17.0 的 macOS 封装实践；未复制该文章正文。
- [calibre 官方项目](https://github.com/kovidgoyal/calibre)，版权归 Kovid Goyal 和各贡献者。
- [官方开发环境说明](https://manual.calibre-ebook.com/develop.html)。
- [bypy 构建工具及依赖构建定义](https://github.com/kovidgoyal/bypy)。

本仓库补丁及脚本按 [GNU GPL v3](LICENSE) 发布。生成应用内保留 calibre 的 LICENSE 和 COPYRIGHT；应用中第三方组件仍受各自许可证约束。Releases 的完整 calibre 源码归档与安装包配套提供。
