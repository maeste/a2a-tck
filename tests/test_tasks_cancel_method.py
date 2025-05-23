import pytest

from tck import message_utils
from tck.sut_client import SUTClient


@pytest.fixture(scope="module")
def sut_client():
    return SUTClient()

@pytest.fixture
def created_task_id(sut_client):
    # Create a task using message/send and return its id
    params = {
        "message": {
            "parts": [
                {"kind": "text", "text": "Task for cancel test"}
            ]
        }
    }
    req = message_utils.make_json_rpc_request("message/send", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    return resp["result"]["id"]

@pytest.mark.core
def test_tasks_cancel_valid(sut_client, created_task_id):
    """
    A2A JSON-RPC Spec: tasks/cancel
    Test canceling a valid task. Expect a Task object in result with state 'canceled'.
    """
    params = {"taskId": created_task_id}
    req = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_success_response(resp, expected_id=req["id"])
    result = resp["result"]
    assert result["id"] == created_task_id
    assert result.get("status", {}).get("state") == "canceled"

@pytest.mark.core
def test_tasks_cancel_nonexistent(sut_client):
    """
    A2A JSON-RPC Spec: tasks/cancel
    Test canceling a non-existent task. Expect TaskNotFoundError.
    """
    params = {"taskId": "nonexistent-task-id"}
    req = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp = sut_client.send_json_rpc(method=req["method"], params=req["params"], id=req["id"])
    assert message_utils.is_json_rpc_error_response(resp, expected_id=req["id"])
    assert resp["error"]["code"] == -32001  # Example: TaskNotFoundError (custom code, may vary)

@pytest.mark.core
def test_tasks_cancel_already_canceled(sut_client, created_task_id):
    """
    A2A JSON-RPC Spec: tasks/cancel
    Test canceling a task that is already canceled. Expect TaskNotCancelableError or similar.
    """
    params = {"taskId": created_task_id}
    # First cancel
    req1 = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp1 = sut_client.send_json_rpc(method=req1["method"], params=req1["params"], id=req1["id"])
    assert message_utils.is_json_rpc_success_response(resp1, expected_id=req1["id"])
    # Second cancel (should fail)
    req2 = message_utils.make_json_rpc_request("tasks/cancel", params=params)
    resp2 = sut_client.send_json_rpc(method=req2["method"], params=req2["params"], id=req2["id"])
    assert message_utils.is_json_rpc_error_response(resp2, expected_id=req2["id"])
    # Error code for TaskNotCancelableError is implementation-specific, so just check error presence
