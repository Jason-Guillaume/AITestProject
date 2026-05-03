"""
根据平台注入的环境变量，为 Selenium 自动合并无头参数（用户无需在脚本里读 HEADLESS_MODE）。

有头模式（HEADLESS_MODE 为假）不打补丁，行为与原生 Selenium 一致。

可通过 AITESTA_SKIP_BROWSER_PATCH=1 关闭。
"""
from __future__ import annotations

import logging
import os
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

_installed = False


def _truthy(val: str | None) -> bool:
    if val is None:
        return False
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _has_headless_arg(options: Any) -> bool:
    try:
        args = getattr(options, "arguments", None) or []
    except Exception:
        args = []
    joined = " ".join(str(a) for a in args)
    if "--headless" in joined or "-headless" in joined:
        return True
    try:
        if getattr(options, "headless", None) is True:
            return True
    except Exception:
        pass
    return False


def install() -> None:
    """在导入用户业务代码之前调用；仅在 HEADLESS_MODE 为真时打补丁。"""
    global _installed
    if _installed:
        return
    _installed = True

    if os.environ.get("AITESTA_SKIP_BROWSER_PATCH", "").strip().lower() in ("1", "true", "yes"):
        logger.debug("AITESTA_SKIP_BROWSER_PATCH set, skip browser patch")
        return

    if not _truthy(os.environ.get("HEADLESS_MODE")):
        return

    try:
        from selenium import webdriver
    except ImportError:
        logger.warning("未安装 selenium，跳过无头自动注入")
        return

    _patch_webdriver_init(webdriver.Chrome, "Chrome", _chrome_options_factory)
    try:
        _patch_webdriver_init(webdriver.Edge, "Edge", _edge_options_factory)
    except Exception as e:
        logger.debug("Edge patch skipped: %s", e)
    try:
        _patch_webdriver_init(webdriver.Firefox, "Firefox", _firefox_options_factory)
    except Exception as e:
        logger.debug("Firefox patch skipped: %s", e)


def _chrome_options_factory():
    from selenium.webdriver.chrome.options import Options

    return Options()


def _edge_options_factory():
    from selenium.webdriver.edge.options import Options

    return Options()


def _firefox_options_factory():
    from selenium.webdriver.firefox.options import Options

    return Options()


def _patch_webdriver_init(
    cls: type,
    name: str,
    options_factory: Callable[[], Any],
) -> None:
    if getattr(cls, "_aitesta_patched", False):
        return

    orig_init = cls.__init__

    @wraps(orig_init)
    def wrapped(self, *args: Any, **kwargs: Any) -> Any:
        options = kwargs.pop("options", None)
        new_args = list(args)
        if options is None and new_args and hasattr(new_args[0], "add_argument"):
            options = new_args.pop(0)
        if options is None:
            options = options_factory()

        if _truthy(os.environ.get("HEADLESS_MODE")) and not _has_headless_arg(options):
            if name == "Firefox":
                try:
                    options.add_argument("-headless")
                except Exception:
                    try:
                        options.headless = True
                    except Exception:
                        pass
            else:
                options.add_argument("--headless=new")

        kwargs["options"] = options
        return orig_init(self, *tuple(new_args), **kwargs)

    cls.__init__ = wrapped  # type: ignore[method-assign]
    setattr(cls, "_aitesta_patched", True)
    logger.info("AITesta: 已为 %s 注入无头参数（HEADLESS_MODE）", name)
