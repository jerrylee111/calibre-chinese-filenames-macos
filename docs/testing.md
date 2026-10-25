# 复现验证

以下测试使用独立临时配置和书库。先把 `APP` 设置为打包后应用的绝对路径，仓库根目录作为当前目录。

```sh
APP=/path/to/calibre.app
TEST_ROOT=$(mktemp -d -t calibre-patch-test)
export CALIBRE_CONFIG_DIRECTORY="$TEST_ROOT/config"
export CALIBRE_PATCH_TEST_DIR="$TEST_ROOT/data"

"$APP/Contents/MacOS/calibre-debug" scripts/check_chinese.py
```

脚本检查：加载的 backend.py 位置；中文作者目录、书名目录与 TXT 文件名；修改元数据后路径更新；正文完整性。检查使用显式异常，避免 calibre 自带 Python 的优化模式忽略 `assert`。

继续测试 GUI，约十秒后自动正常退出：

```sh
export CALIBRE_GUI_TEST_LIBRARY="$TEST_ROOT/data/library"
export CALIBRE_GUI_TEST_RESULT="$TEST_ROOT/gui-result.txt"
"$APP/Contents/MacOS/calibre-debug" scripts/check_gui.py
cat "$CALIBRE_GUI_TEST_RESULT"
```

预期结果为 `PASS`。GUI 测试使用单独的进程锁与通信地址，避免转发到日常 calibre 实例；只允许对临时书库进行测试。

转换测试可用临时书库中的 TXT：

```sh
"$APP/Contents/MacOS/ebook-convert" \
  "$TEST_ROOT/data/library/中文作者/中文书名测试 (1)/中文书名测试 - 中文作者.txt" \
  "$TEST_ROOT/test.epub" --input-encoding=utf-8
```

签名检查：

```sh
codesign --verify --deep --strict "$APP"
```

路径与只读验证：将 DMG 以只读方式挂载到包含中文和空格的路径，将 `APP` 指向镜像内的应用，使用新的 `TEST_ROOT` 重复以上步骤，并在退出后再次验证签名。

测试通过不等同于覆盖所有 calibre 功能；原始四行补丁的特殊字符和超长文件名限制仍然存在。Intel 版本包含在应用内，但初始发行未在 Intel 硬件上测试。
