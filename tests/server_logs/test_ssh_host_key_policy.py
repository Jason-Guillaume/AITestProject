"""server_logs SSH 主机密钥策略（纯单元，不连真实 SSH）。"""

from unittest.mock import MagicMock

import paramiko
import pytest

from server_logs.ssh_tail import apply_ssh_host_key_policy


def test_apply_auto_add_uses_auto_add_policy():
    client = MagicMock()
    apply_ssh_host_key_policy(client, paramiko, policy="auto_add")
    client.set_missing_host_key_policy.assert_called_once()
    policy_obj = client.set_missing_host_key_policy.call_args[0][0]
    assert isinstance(policy_obj, paramiko.AutoAddPolicy)


def test_apply_warning_uses_warning_policy():
    client = MagicMock()
    apply_ssh_host_key_policy(client, paramiko, policy="warning")
    policy_obj = client.set_missing_host_key_policy.call_args[0][0]
    assert isinstance(policy_obj, paramiko.WarningPolicy)


def test_apply_reject_loads_system_keys_and_rejects():
    client = MagicMock()
    apply_ssh_host_key_policy(client, paramiko, policy="reject")
    client.load_system_host_keys.assert_called_once()
    policy_obj = client.set_missing_host_key_policy.call_args[0][0]
    assert isinstance(policy_obj, paramiko.RejectPolicy)


def test_apply_known_hosts_requires_path():
    client = MagicMock()
    with pytest.raises(ValueError, match="KNOWN_HOSTS"):
        apply_ssh_host_key_policy(client, paramiko, policy="known_hosts", known_hosts_path="")


def test_apply_known_hosts_loads_file():
    client = MagicMock()
    apply_ssh_host_key_policy(
        client, paramiko, policy="known_hosts", known_hosts_path="/tmp/dummy_known_hosts"
    )
    client.load_host_keys.assert_called_once_with("/tmp/dummy_known_hosts")
    policy_obj = client.set_missing_host_key_policy.call_args[0][0]
    assert isinstance(policy_obj, paramiko.RejectPolicy)


def test_unknown_policy_raises():
    client = MagicMock()
    with pytest.raises(ValueError, match="未知"):
        apply_ssh_host_key_policy(client, paramiko, policy="invalid-mode")
