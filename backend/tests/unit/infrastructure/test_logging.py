import json
import logging

from taskmanager.infrastructure.logging import JsonFormatter, configure_logging, request_id_var


def test_json_lines_carry_the_request_id_and_extra_fields() -> None:
    configure_logging("INFO", "json")
    token = request_id_var.set("req-1")
    try:
        record = logging.getLogger("t").makeRecord(
            "t", logging.INFO, __file__, 1, "hello %s", ("world",), None, extra={"status": 200}
        )
    finally:
        request_id_var.reset(token)

    line = json.loads(JsonFormatter().format(record))

    assert line["message"] == "hello world"
    assert line["request_id"] == "req-1"
    assert line["status"] == 200
    assert line["level"] == "INFO"


def test_configure_logging_is_idempotent() -> None:
    configure_logging("INFO", "text")
    configure_logging("INFO", "json")

    ours = [h for h in logging.getLogger().handlers if h.get_name() == "taskmanager"]
    assert len(ours) == 1
    assert isinstance(ours[0].formatter, JsonFormatter)
