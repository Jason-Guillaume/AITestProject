import time
import json
import logging
from datetime import datetime
from urllib.parse import urljoin

from django.core.cache import cache

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import Select
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from assistant.keyword_driven_models import KWTestCase

logger = logging.getLogger(__name__)


class CancelledError(Exception):
    pass


def _check_cancel(execution_id):
    redis_client = cache.client.get_client()
    cancel_key = f"kw_execution:{execution_id}:cancel"
    if redis_client.exists(cancel_key):
        redis_client.delete(cancel_key)
        raise CancelledError()


BY_MAP = {
    "By.ID": By.ID if SELENIUM_AVAILABLE else "id",
    "By.NAME": By.NAME if SELENIUM_AVAILABLE else "name",
    "By.XPATH": By.XPATH if SELENIUM_AVAILABLE else "xpath",
    "By.CSS_SELECTOR": By.CSS_SELECTOR if SELENIUM_AVAILABLE else "css selector",
    "By.CLASS_NAME": By.CLASS_NAME if SELENIUM_AVAILABLE else "class name",
    "By.TAG_NAME": By.TAG_NAME if SELENIUM_AVAILABLE else "tag name",
    "By.LINK_TEXT": By.LINK_TEXT if SELENIUM_AVAILABLE else "link text",
    "By.PARTIAL_LINK_TEXT": By.PARTIAL_LINK_TEXT if SELENIUM_AVAILABLE else "partial link text",
}


def _get_redis_client():
    return cache.client.get_client()


def _write_log(execution_id, log_type, message):
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": log_type,
            "message": message.rstrip("\n"),
        }
        log_key = f"kw_execution:{execution_id}:logs"
        redis_client = _get_redis_client()
        pipe = redis_client.pipeline()
        pipe.rpush(log_key, json.dumps(log_entry))
        pipe.expire(log_key, 86400)
        pipe.execute()
    except Exception as e:
        logger.error("写入日志到Redis失败: %s", e, exc_info=True)


def _update_status(execution_id, status, **kwargs):
    try:
        status_data = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            **kwargs,
        }
        status_key = f"kw_execution:{execution_id}:status"
        redis_client = _get_redis_client()
        redis_client.set(status_key, json.dumps(status_data), ex=86400)
    except Exception as e:
        logger.error("更新状态到Redis失败: %s", e, exc_info=True)


def _write_step_result(execution_id, step_result):
    try:
        steps_key = f"kw_execution:{execution_id}:steps"
        redis_client = _get_redis_client()
        pipe = redis_client.pipeline()
        pipe.rpush(steps_key, json.dumps(step_result))
        pipe.expire(steps_key, 86400)
        pipe.execute()
    except Exception as e:
        logger.error("写入步骤结果到Redis失败: %s", e, exc_info=True)


def _resolve_by(by_str):
    return BY_MAP.get(by_str, By.XPATH if SELENIUM_AVAILABLE else "xpath")


def _create_driver(browser_type, headless):
    if not SELENIUM_AVAILABLE:
        raise RuntimeError("selenium 未安装，无法创建 WebDriver")

    bt = (browser_type or "chrome").strip().lower()

    if bt == "edge":
        options = webdriver.EdgeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Edge(options=options)

    if bt == "firefox":
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        return webdriver.Firefox(options=options)

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)


def _resolve_variables(text, variables):
    if not text or not variables:
        return text
    result = text
    for key, val in variables.items():
        placeholder = "${" + str(key) + "}"
        if placeholder in result:
            result = result.replace(placeholder, str(val))
    return result


def _execute_assert(driver, step, base_url):
    assert_type = step.get("assert_type", "")
    expected = step.get("expected", "")
    locator = step.get("locator")

    if assert_type == "url_contains":
        actual = driver.current_url
        if expected not in actual:
            raise AssertionError(
                f"URL断言失败: 期望URL包含 '{expected}', 实际URL为 '{actual}'"
            )
        return

    if assert_type == "title_contains":
        actual = driver.title
        if expected not in actual:
            raise AssertionError(
                f"标题断言失败: 期望标题包含 '{expected}', 实际标题为 '{actual}'"
            )
        return

    if assert_type == "element_count":
        if not locator:
            raise AssertionError("element_count断言需要关联元素定位器")
        by = _resolve_by(locator.get("by", "By.XPATH"))
        expression = locator.get("expression", "")
        elements = driver.find_elements(by, expression)
        expected_count = int(expected)
        actual_count = len(elements)
        if actual_count != expected_count:
            raise AssertionError(
                f"元素数量断言失败: 期望 {expected_count}, 实际 {actual_count}"
            )
        return

    if not locator:
        raise AssertionError(f"断言类型 '{assert_type}' 需要关联元素定位器")

    by = _resolve_by(locator.get("by", "By.XPATH"))
    expression = locator.get("expression", "")
    element = driver.find_element(by, expression)

    if assert_type == "visible":
        if not element.is_displayed():
            raise AssertionError("元素可见性断言失败: 期望元素可见, 实际不可见")
        return

    if assert_type == "not_visible":
        if element.is_displayed():
            raise AssertionError("元素可见性断言失败: 期望元素不可见, 实际可见")
        return

    if assert_type == "text_equals":
        actual = element.text
        if actual != expected:
            raise AssertionError(
                f"文本断言失败: 期望 '{expected}', 实际 '{actual}'"
            )
        return

    if assert_type == "text_contains":
        actual = element.text
        if expected not in actual:
            raise AssertionError(
                f"文本包含断言失败: 期望包含 '{expected}', 实际 '{actual}'"
            )
        return

    if assert_type == "attribute_equals":
        sep_idx = expected.find("=")
        if sep_idx < 0:
            raise AssertionError(
                f"属性断言格式错误: 期望 'attribute_name=expected_value', 实际 '{expected}'"
            )
        attr_name = expected[:sep_idx]
        attr_value = expected[sep_idx + 1:]
        actual = element.get_attribute(attr_name)
        if actual != attr_value:
            raise AssertionError(
                f"属性断言失败: 属性 '{attr_name}' 期望 '{attr_value}', 实际 '{actual}'"
            )
        return

    raise AssertionError(f"不支持的断言类型: {assert_type}")


def _execute_step(driver, wait, step, base_url, variables):
    action = step.get("action", "")
    value = step.get("value", "")
    locator = step.get("locator")

    value = _resolve_variables(value, variables)

    if action == "navigate":
        url = urljoin(base_url, value) if base_url else value
        driver.get(url)
        return

    if action == "click":
        if not locator:
            raise ValueError("click操作需要关联元素定位器")
        by = _resolve_by(locator.get("by", "By.XPATH"))
        expression = _resolve_variables(locator.get("expression", ""), variables)
        element = wait.until(EC.element_to_be_clickable((by, expression)))
        element.click()
        return

    if action == "input":
        if not locator:
            raise ValueError("input操作需要关联元素定位器")
        by = _resolve_by(locator.get("by", "By.XPATH"))
        expression = _resolve_variables(locator.get("expression", ""), variables)
        element = driver.find_element(by, expression)
        element.clear()
        element.send_keys(value)
        return

    if action == "assert":
        _execute_assert(driver, step, base_url)
        return

    if action == "hover":
        if not locator:
            raise ValueError("hover操作需要关联元素定位器")
        by = _resolve_by(locator.get("by", "By.XPATH"))
        expression = _resolve_variables(locator.get("expression", ""), variables)
        element = driver.find_element(by, expression)
        ActionChains(driver).move_to_element(element).perform()
        return

    if action == "select":
        if not locator:
            raise ValueError("select操作需要关联元素定位器")
        by = _resolve_by(locator.get("by", "By.XPATH"))
        expression = _resolve_variables(locator.get("expression", ""), variables)
        element = driver.find_element(by, expression)
        Select(element).select_by_value(value)
        return

    if action == "wait":
        if not locator:
            raise ValueError("wait操作需要关联元素定位器")
        by = _resolve_by(locator.get("by", "By.XPATH"))
        expression = _resolve_variables(locator.get("expression", ""), variables)
        wait.until(EC.presence_of_element_located((by, expression)))
        return

    if action == "sleep":
        time.sleep(float(value))
        return

    if action == "switch_window":
        index = int(value)
        driver.switch_to.window(driver.window_handles[index])
        return

    if action == "switch_frame":
        try:
            driver.switch_to.frame(int(value))
        except (ValueError, TypeError):
            driver.switch_to.frame(value)
        return

    if action == "scroll":
        if not locator:
            raise ValueError("scroll操作需要关联元素定位器")
        by = _resolve_by(locator.get("by", "By.XPATH"))
        expression = _resolve_variables(locator.get("expression", ""), variables)
        element = driver.find_element(by, expression)
        driver.execute_script("arguments[0].scrollIntoView();", element)
        return

    if action == "execute_js":
        driver.execute_script(value)
        return

    raise ValueError(f"不支持的操作类型: {action}")


def execute_kw_test_case(test_case_id, execution_id, browser_type="chrome", headless=True):
    driver = None
    start_time = time.time()

    try:
        _update_status(execution_id, "running", test_case_id=test_case_id, started_at=datetime.now().isoformat())
        _write_log(execution_id, "system", f"开始执行关键字用例 (ID: {test_case_id}, 执行ID: {execution_id})")

        try:
            test_case = KWTestCase.objects.get(pk=test_case_id)
        except KWTestCase.DoesNotExist:
            raise RuntimeError(f"关键字用例不存在 (ID: {test_case_id})")

        blueprint = test_case.to_executor_dict()
        base_url = blueprint.get("base_url", "")
        variables = blueprint.get("variables", {})
        timeout_seconds = blueprint.get("timeout_seconds", 300)
        steps = blueprint.get("steps", [])

        _write_log(execution_id, "system", f"用例名称: {blueprint.get('name', '')}")
        _write_log(execution_id, "system", f"基础URL: {base_url}")
        _write_log(execution_id, "system", f"步骤数: {len(steps)}")
        _write_log(execution_id, "system", f"浏览器: {browser_type} (无头模式: {headless})")

        if not SELENIUM_AVAILABLE:
            raise RuntimeError("selenium 未安装，无法执行关键字用例")

        driver = _create_driver(browser_type, headless)
        driver.set_page_load_timeout(timeout_seconds)
        wait = WebDriverWait(driver, timeout_seconds)

        _write_log(execution_id, "system", "WebDriver 已创建")
        _write_log(execution_id, "system", "=" * 60)

        overall_passed = True

        for step in steps:
            step_number = step.get("step", 0)
            action = step.get("action", "")
            action_label = step.get("action_label", action)
            description = step.get("description", "")
            enabled = step.get("enabled", True)

            if not enabled:
                _write_log(execution_id, "system", f"Step {step_number}: {action_label} - 已跳过（未启用）")
                _write_step_result(execution_id, {
                    "step": step_number,
                    "action": action,
                    "status": "skipped",
                    "error": None,
                    "duration_ms": 0,
                })
                continue

            _check_cancel(execution_id)

            step_start = time.time()
            step_desc = f"Step {step_number}: {action_label}"
            if description:
                step_desc += f" - {description}"
            _write_log(execution_id, "system", step_desc)

            try:
                _execute_step(driver, wait, step, base_url, variables)
                duration_ms = int((time.time() - step_start) * 1000)
                _write_log(execution_id, "system", f"Step {step_number}: 通过 ({duration_ms}ms)")
                _write_step_result(execution_id, {
                    "step": step_number,
                    "action": action,
                    "status": "passed",
                    "error": None,
                    "duration_ms": duration_ms,
                })
            except Exception as e:
                duration_ms = int((time.time() - step_start) * 1000)
                error_msg = f"{type(e).__name__}: {e}"
                overall_passed = False
                _write_log(execution_id, "system", f"Step {step_number}: 失败 - {error_msg} ({duration_ms}ms)")
                _write_step_result(execution_id, {
                    "step": step_number,
                    "action": action,
                    "status": "failed",
                    "error": error_msg,
                    "duration_ms": duration_ms,
                })

        duration = time.time() - start_time
        final_status = "success" if overall_passed else "failed"

        _write_log(execution_id, "system", "=" * 60)
        _write_log(execution_id, "system", f"执行完成: {final_status} (总耗时: {duration:.2f}秒)")
        _write_log(execution_id, "system", "=" * 60)

        _update_status(execution_id, final_status, test_case_id=test_case_id, duration=duration, completed_at=datetime.now().isoformat())

    except CancelledError:
        duration = time.time() - start_time

        try:
            _write_log(execution_id, "system", "执行已被用户取消")
        except Exception:
            pass

        try:
            _update_status(execution_id, "cancelled", test_case_id=test_case_id, duration=duration, completed_at=datetime.now().isoformat())
        except Exception:
            pass

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        duration = time.time() - start_time
        logger.error("关键字用例执行异常: %s", error_msg, exc_info=True)

        try:
            _write_log(execution_id, "system", f"执行异常: {error_msg}")
        except Exception:
            pass

        try:
            _update_status(execution_id, "failed", test_case_id=test_case_id, error=error_msg, duration=duration, completed_at=datetime.now().isoformat())
        except Exception:
            pass

    finally:
        if driver is not None:
            try:
                driver.quit()
                _write_log(execution_id, "system", "WebDriver 已关闭")
            except Exception as e:
                logger.warning("关闭WebDriver失败: %s", e)
