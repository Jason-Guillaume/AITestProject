# 测试覆盖率报告（htmlcov）

## 功能概述
`htmlcov` 目录由 **pytest‑cov** 生成，存放基于 **HTML** 的单元测试覆盖率报告。开发者可通过浏览器直观看到每个文件、每行代码的覆盖情况，帮助发现未被测试的关键路径。

## 关键文件结构
```
htmlcov/
├─ index.html            # 总览页面，展示整体覆盖率百分比、执行时间等摘要
├─ <module>.html        # 每个 Python 模块的详细覆盖率页面
└─ coverage.xml          # XML 格式的覆盖率数据（用于 CI 报告）
```

## 使用方式
1. **生成报告**：在项目根目录执行 `pytest --cov=. --cov-report=html`。
2. **本地查看**：运行完成后，打开 `htmlcov/index.html` 即可在浏览器中查看。
3. **CI 集成**：CI（GitHub Actions、GitLab CI）可将 `coverage.xml` 上传至 Codecov 或 Coveralls，自动评估覆盖率阈值。

## 常见错误与排查
* **报告未生成**：确认已安装 `pytest-cov`，并在 `pytest.ini` 中启用 `addopts = --cov=. --cov-report=html`。
* **文件路径错误**：如果项目使用了 `src/` 结构，需要在 `--cov=src` 中指定正确路径。
* **覆盖率阈值不达标**：CI 中可使用 `--cov-fail-under=80` 强制最低覆盖率，确保关键代码都有测试。

---
