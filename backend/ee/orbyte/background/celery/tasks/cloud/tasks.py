import time

from celery import shared_task
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from redis.lock import Lock as RedisLock

from ee.orbyte.server.tenants.product_gating import get_gated_tenants
from orbyte.background.celery.apps.app_base import task_logger
from orbyte.background.celery.tasks.beat_schedule import BEAT_EXPIRES_DEFAULT
from orbyte.configs.constants import CELERY_GENERIC_BEAT_LOCK_TIMEOUT
from orbyte.configs.constants import ORBYTE_CLOUD_TENANT_ID
from orbyte.configs.constants import OrbyteCeleryPriority
from orbyte.configs.constants import OrbyteCeleryTask
from orbyte.configs.constants import OrbyteRedisLocks
from orbyte.db.engine.tenant_utils import get_all_tenant_ids
from orbyte.redis.redis_pool import get_redis_client
from orbyte.redis.redis_pool import redis_lock_dump
from orbyte.redis.redis_tenant_work_gating import cleanup_expired
from orbyte.redis.redis_tenant_work_gating import get_active_tenants
from orbyte.redis.redis_tenant_work_gating import observe_active_set_size
from orbyte.redis.redis_tenant_work_gating import record_full_fanout_cycle
from orbyte.redis.redis_tenant_work_gating import record_gate_decision
from orbyte.redis.tenant_redis_client import TenantRedisClient
from orbyte.server.runtime.orbyte_runtime import OrbyteRuntime
from shared_configs.configs import IGNORED_SYNCING_TENANT_LIST

_FULL_FANOUT_TIMESTAMP_KEY_PREFIX = "tenant_work_gating_last_full_fanout_ms"


def _should_bypass_gate_for_full_fanout(
    redis_client: TenantRedisClient, task_name: str, interval_seconds: int
) -> bool:
    """True if at least `interval_seconds` have elapsed since the last
    full-fanout bypass for this task. On True, updates the stored timestamp
    atomically-enough (it's a best-effort counter, not a lock)."""
    key = f"{_FULL_FANOUT_TIMESTAMP_KEY_PREFIX}:{task_name}"
    now_ms = int(time.time() * 1000)
    threshold_ms = now_ms - (interval_seconds * 1000)

    try:
        raw = redis_client.get(key)
    except Exception:
        task_logger.exception(f"full-fanout timestamp read failed: task={task_name}")
        # Fail open: treat as "interval elapsed" so we don't skip every
        # tenant during a Redis hiccup.
        return True

    if raw is None:
        # First invocation — bypass so the set seeds cleanly.
        elapsed = True
    else:
        try:
            last_ms = int(raw.decode())
            elapsed = last_ms <= threshold_ms
        except ValueError:
            elapsed = True

    if elapsed:
        try:
            redis_client.set(key, str(now_ms))
        except Exception:
            task_logger.exception(
                f"full-fanout timestamp write failed: task={task_name}"
            )
    return elapsed


@shared_task(
    name=OrbyteCeleryTask.CLOUD_BEAT_TASK_GENERATOR,
    ignore_result=True,
    trail=False,
    bind=True,
)
def cloud_beat_task_generator(
    self: Task,
    task_name: str,
    queue: str = OrbyteCeleryTask.DEFAULT,
    priority: int = OrbyteCeleryPriority.MEDIUM,
    expires: int = BEAT_EXPIRES_DEFAULT,
    skip_gated: bool = True,
    work_gated: bool = False,
) -> bool | None:
    """a lightweight task used to kick off individual beat tasks per tenant."""
    time_start = time.monotonic()

    redis_client = get_redis_client(tenant_id=ORBYTE_CLOUD_TENANT_ID)

    lock_beat: RedisLock = redis_client.lock(
        f"{OrbyteRedisLocks.CLOUD_BEAT_TASK_GENERATOR_LOCK}:{task_name}",
        timeout=CELERY_GENERIC_BEAT_LOCK_TIMEOUT,
    )

    # these tasks should never overlap
    if not lock_beat.acquire(blocking=False):
        return None

    last_lock_time = time.monotonic()
    tenant_ids: list[str] = []
    num_processed_tenants = 0
    num_skipped_gated = 0
    num_would_skip_work_gate = 0
    num_skipped_work_gate = 0

    # Tenant-work-gating read path. Resolve once per invocation.
    gate_enabled = False
    gate_enforce = False
    full_fanout_cycle = False
    active_tenants: set[str] | None = None

    try:
        # Gating setup is inside the try block so any exception still
        # reaches the finally that releases the beat lock.
        if work_gated:
            try:
                gate_enabled = OrbyteRuntime.get_tenant_work_gating_enabled()
                gate_enforce = OrbyteRuntime.get_tenant_work_gating_enforce()
            except Exception:
                task_logger.exception("tenant work gating: runtime flag read failed")
                gate_enabled = False

            if gate_enabled:
                redis_failed = False
                interval_s = (
                    OrbyteRuntime.get_tenant_work_gating_full_fanout_interval_seconds()
                )
                full_fanout_cycle = _should_bypass_gate_for_full_fanout(
                    redis_client, task_name, interval_s
                )
                if full_fanout_cycle:
                    record_full_fanout_cycle(task_name)
                    try:
                        ttl_s = OrbyteRuntime.get_tenant_work_gating_ttl_seconds()
                        cleanup_expired(ttl_s)
                    except Exception:
                        task_logger.exception(
                            "tenant work gating: cleanup_expired failed"
                        )
                else:
                    ttl_s = OrbyteRuntime.get_tenant_work_gating_ttl_seconds()
                    active_tenants = get_active_tenants(ttl_s)
                    if active_tenants is None:
                        full_fanout_cycle = True
                        record_full_fanout_cycle(task_name)
                        redis_failed = True

                # Only refresh the gauge when Redis is known-reachable —
                # skip the ZCARD if we just failed open due to a Redis error.
                if not redis_failed:
                    observe_active_set_size()

        tenant_ids = get_all_tenant_ids()

        # Per-task control over whether gated tenants are included. Most periodic tasks
        # do no useful work on gated tenants and just waste DB connections fanning out
        # to ~10k+ inactive tenants. A small number of cleanup tasks (connector deletion,
        # checkpoint/index attempt cleanup) need to run on gated tenants and pass
        # `skip_gated=False` from the beat schedule.
        gated_tenants: set[str] = get_gated_tenants() if skip_gated else set()

        for tenant_id in tenant_ids:
            if tenant_id in gated_tenants:
                num_skipped_gated += 1
                continue

            current_time = time.monotonic()
            if current_time - last_lock_time >= (CELERY_GENERIC_BEAT_LOCK_TIMEOUT / 4):
                lock_beat.reacquire()
                last_lock_time = current_time

            # needed in the cloud
            if IGNORED_SYNCING_TENANT_LIST and tenant_id in IGNORED_SYNCING_TENANT_LIST:
                continue

            # Tenant work gate: if the feature is on, check membership. Skip
            # unmarked tenants when enforce=True AND we're not in a full-
            # fanout cycle. Always log/emit the shadow counter.
            if work_gated and gate_enabled and not full_fanout_cycle:
                would_skip = (
                    active_tenants is not None and tenant_id not in active_tenants
                )
                if would_skip:
                    num_would_skip_work_gate += 1
                    if gate_enforce:
                        num_skipped_work_gate += 1
                        record_gate_decision(task_name, skipped=True)
                        continue
                    record_gate_decision(task_name, skipped=False)

            self.app.send_task(
                task_name,
                kwargs=dict(
                    tenant_id=tenant_id,
                ),
                queue=queue,
                priority=priority,
                expires=expires,
                ignore_result=True,
            )

            num_processed_tenants += 1
    except SoftTimeLimitExceeded:
        task_logger.info(
            "Soft time limit exceeded, task is being terminated gracefully."
        )
    except Exception:
        task_logger.exception("Unexpected exception during cloud_beat_task_generator")
    finally:
        if not lock_beat.owned():
            task_logger.error(
                "cloud_beat_task_generator - Lock not owned on completion"
            )
            redis_lock_dump(lock_beat, redis_client)
        else:
            lock_beat.release()

    time_elapsed = time.monotonic() - time_start
    task_logger.info(
        f"cloud_beat_task_generator finished: "
        f"task={task_name} "
        f"num_processed_tenants={num_processed_tenants} "
        f"num_skipped_gated={num_skipped_gated} "
        f"num_would_skip_work_gate={num_would_skip_work_gate} "
        f"num_skipped_work_gate={num_skipped_work_gate} "
        f"full_fanout_cycle={full_fanout_cycle} "
        f"work_gated={work_gated} "
        f"gate_enabled={gate_enabled} "
        f"gate_enforce={gate_enforce} "
        f"num_tenants={len(tenant_ids)} "
        f"elapsed={time_elapsed:.2f}"
    )
    return True
