import pytest
from pytest_bdd import given, parsers, then

from taskmanager.infrastructure.config import Settings
from taskmanager.infrastructure.tasks import jobs  # noqa: F401 — registers the jobs
from taskmanager.infrastructure.tasks.celery_app import celery_app, create_celery_app
from taskmanager.infrastructure.tasks.publisher import CeleryEventPublisher
from taskmanager.infrastructure.tasks.runtime import WorkerRuntime, configure_worker
from tests.fakes import RecordingNotifier
from tests.step_defs.patterns import QUOTED as Q
from tests.step_defs.world import World


@given("background jobs run immediately")
def background_jobs_run_eagerly(
    world: World, test_settings: Settings, request: pytest.FixtureRequest
) -> None:
    notifier = RecordingNotifier()
    configure_worker(WorkerRuntime(settings=test_settings, notifier=notifier))
    previous = {k: celery_app.conf[k] for k in ("task_always_eager", "task_eager_propagates")}
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    request.addfinalizer(lambda: celery_app.conf.update(previous))
    world.container.event_publisher = CeleryEventPublisher(
        celery_app, timeout_seconds=test_settings.event_publish_timeout_seconds
    )
    world.notifier = notifier
    request.addfinalizer(lambda: configure_worker(None))


@given("the background job broker is unavailable")
def broker_unavailable(world: World, test_settings: Settings) -> None:
    dead_broker = test_settings.model_copy(
        update={"celery_broker_url": "redis://127.0.0.1:1/0", "celery_task_always_eager": False}
    )
    world.container.event_publisher = CeleryEventPublisher(
        create_celery_app(dead_broker),
        timeout_seconds=test_settings.event_publish_timeout_seconds,
    )


@then(
    parsers.re(f"{Q.format('email')} should receive a notification mentioning {Q.format('text')}")
)
def receives_notification(world: World, email: str, text: str) -> None:
    assert world.notifier is not None
    messages = [n for n in world.notifier.sent if n.recipient.email == email]
    assert any(text in n.subject or text in n.body for n in messages), world.notifier.sent


@then(parsers.re(f"{Q.format('email')} should not receive a notification about completion"))
def receives_no_completion_notification(world: World, email: str) -> None:
    assert world.notifier is not None
    assert not [
        n
        for n in world.notifier.sent
        if n.recipient.email == email and "completed" in n.subject.lower()
    ]


@then(parsers.parse("the response should arrive within {seconds:d} seconds"))
def response_is_fast(world: World, seconds: int) -> None:
    assert world.response.elapsed.total_seconds() < seconds, world.response.elapsed


@then("no notification should be sent")
def no_notification(world: World) -> None:
    assert world.notifier is not None
    assert world.notifier.sent == []


@then("no background job should have failed")
def no_job_failed(caplog: pytest.LogCaptureFixture) -> None:
    failures = [
        r for r in caplog.records if r.name.endswith("publisher") and r.levelname == "ERROR"
    ]
    assert failures == [], [r.getMessage() for r in failures]


@then("the enqueue failure should be logged")
def enqueue_failure_logged(caplog: pytest.LogCaptureFixture) -> None:
    assert any(
        r.name.endswith("publisher") and "Could not enqueue" in r.getMessage()
        for r in caplog.records
    )
