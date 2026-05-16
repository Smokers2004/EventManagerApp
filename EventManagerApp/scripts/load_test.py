import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from django.conf import settings
from django.db import OperationalError
from django.test import Client

from scripts._benchmark_utils import cleanup_dataset, create_dataset


def percentile_95(values):
    if not values:
        return 0.0
    index = max(0, int(len(values) * 0.95) - 1)
    return sorted(values)[index]


def build_auth_cookies(user):
    client = Client()
    client.force_login(user)
    return {
        key: morsel.value
        for key, morsel in client.cookies.items()
        if key == settings.SESSION_COOKIE_NAME
    }


def run_parallel_scenario(scenario, ctx):
    auth_cookies = build_auth_cookies(scenario["user"])

    def make_request(index):
        last_error = None
        for attempt in range(4):
            client = Client()
            for key, value in auth_cookies.items():
                client.cookies[key] = value

            started = time.perf_counter()
            try:
                if scenario["method"] == "GET":
                    response = client.get(scenario["path"])
                else:
                    if scenario["name"] == "message_send":
                        payload = {
                            "receiver": ctx.assistant.pk,
                            "subject": f"{ctx.prefix}_load_post_{index}",
                            "body": "Parallel load test message.",
                        }
                    elif scenario["name"] == "participant_add":
                        payload = {
                            "event": ctx.event_ids[index % len(ctx.event_ids)],
                            "fullname": f"{ctx.prefix}_load_participant_{index}",
                            "gender": "male" if index % 2 == 0 else "female",
                            "phone": f"+7999555{index:04d}",
                            "email": f"{ctx.prefix}_load_participant_{index}@test.local",
                        }
                    elif scenario["name"] == "expense_add":
                        payload = {
                            "event": ctx.event_ids[index % len(ctx.event_ids)],
                            "c": ctx.contractor_id,
                            "product": f"{ctx.prefix}_load_expense_{index}",
                            "quantity": 1 + (index % 3),
                            "price": 1000 + (index % 5) * 250,
                            "date": "20.04.2026",
                        }
                    elif scenario["name"] == "bind_employees":
                        payload = {
                            "employees": [ctx.admin.pk, ctx.manager.pk],
                        }
                    else:
                        payload = {}
                    response = client.post(scenario["path"], payload)
                elapsed_ms = (time.perf_counter() - started) * 1000
                return elapsed_ms, response.status_code
            except OperationalError as exc:
                last_error = exc
                if "locked" not in str(exc).lower() or attempt == 3:
                    raise
                time.sleep(0.05 * (attempt + 1))

        raise last_error

    times = []
    statuses = []
    started_batch = time.perf_counter()
    with ThreadPoolExecutor(max_workers=scenario["workers"]) as executor:
        futures = [executor.submit(make_request, idx) for idx in range(scenario["requests"])]
        for future in as_completed(futures):
            elapsed_ms, status = future.result()
            times.append(elapsed_ms)
            statuses.append(status)
    elapsed_batch = time.perf_counter() - started_batch

    success_count = sum(1 for status in statuses if status in {200, 302})
    return {
        "success_rate": round(success_count / len(statuses) * 100, 2),
        "avg_ms": round(statistics.mean(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "p95_ms": round(percentile_95(times), 2),
        "rps": round(len(times) / elapsed_batch, 2),
        "statuses": sorted(set(statuses)),
    }


def main():
    ctx = create_dataset(
        events_count=18,
        participants_per_event=18,
        tasks_per_event=8,
        orders_per_event=6,
        messages_count=60,
    )

    main_event_id = ctx.event_ids[0]
    message_id = ctx.message_ids[0]
    scenarios = [
        {
            "name": "home",
            "method": "GET",
            "path": "/",
            "user": ctx.admin,
            "workers": 20,
            "requests": 200,
        },
        {
            "name": "events",
            "method": "GET",
            "path": "/events/",
            "user": ctx.admin,
            "workers": 20,
            "requests": 200,
        },
        {
            "name": "event_detail",
            "method": "GET",
            "path": f"/events/{main_event_id}/",
            "user": ctx.admin,
            "workers": 20,
            "requests": 200,
        },
        {
            "name": "participants",
            "method": "GET",
            "path": "/participants/",
            "user": ctx.admin,
            "workers": 20,
            "requests": 200,
        },
        {
            "name": "expenses",
            "method": "GET",
            "path": "/expenses/",
            "user": ctx.admin,
            "workers": 20,
            "requests": 200,
        },
        {
            "name": "messages",
            "method": "GET",
            "path": "/messages/",
            "user": ctx.assistant,
            "workers": 20,
            "requests": 200,
        },
        {
            "name": "message_detail",
            "method": "GET",
            "path": f"/messages/{message_id}/",
            "user": ctx.assistant,
            "workers": 20,
            "requests": 200,
        },
        {
            "name": "message_send",
            "method": "POST",
            "path": "/messages/",
            "user": ctx.manager,
            "workers": 8,
            "requests": 60,
        },
        {
            "name": "participant_add",
            "method": "POST",
            "path": "/participants/add/",
            "user": ctx.admin,
            "workers": 8,
            "requests": 60,
        },
        {
            "name": "expense_add",
            "method": "POST",
            "path": "/expenses/add/",
            "user": ctx.admin,
            "workers": 8,
            "requests": 60,
        },
        {
            "name": "bind_employees",
            "method": "POST",
            "path": f"/events/{main_event_id}/bindings/",
            "user": ctx.admin,
            "workers": 8,
            "requests": 60,
        },
        {
            "name": "report_generate_event",
            "method": "POST",
            "path": f"/reports/generate/{main_event_id}/event/",
            "user": ctx.teamlead,
            "workers": 5,
            "requests": 20,
        },
        {
            "name": "report_generate_expense",
            "method": "POST",
            "path": f"/reports/generate/{main_event_id}/expense/",
            "user": ctx.teamlead,
            "workers": 5,
            "requests": 20,
        },
    ]

    try:
        print("LOAD_DATASET_START")
        print(f"events={len(ctx.event_ids)}")
        print(f"participants={len(ctx.participant_ids)}")
        print(f"tasks={len(ctx.task_ids)}")
        print(f"orders={len(ctx.order_ids)}")
        print(f"messages={len(ctx.message_ids)}")
        print("LOAD_DATASET_END")
        print("LOAD_RESULTS_START")
        for scenario in scenarios:
            result = run_parallel_scenario(scenario, ctx)
            print(
                f"{scenario['name']}|{scenario['method']}|{scenario['path']}|"
                f"workers={scenario['workers']}|requests={scenario['requests']}|"
                f"success={result['success_rate']}|avg={result['avg_ms']}|min={result['min_ms']}|"
                f"max={result['max_ms']}|p95={result['p95_ms']}|rps={result['rps']}|"
                f"status={result['statuses']}"
            )
        print("LOAD_RESULTS_END")
    finally:
        cleanup_dataset(ctx)


if __name__ == "__main__":
    main()
