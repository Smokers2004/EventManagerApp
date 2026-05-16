import statistics
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from django.conf import settings
from django.test import Client

from scripts._benchmark_utils import cleanup_dataset, create_dataset
from main.models import Report


def percentile_95(values):
    if not values:
        return 0.0
    index = max(0, int(len(values) * 0.95) - 1)
    return sorted(values)[index]


def benchmark_get(client, path, iterations=20):
    times = []
    statuses = set()
    for _ in range(iterations):
        started = time.perf_counter()
        response = client.get(path)
        times.append((time.perf_counter() - started) * 1000)
        statuses.add(response.status_code)
    return {
        "avg_ms": round(statistics.mean(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "p95_ms": round(percentile_95(times), 2),
        "statuses": sorted(statuses),
    }


def benchmark_report_generation(client, event_id, report_type):
    started = time.perf_counter()
    response = client.post(f"/reports/generate/{event_id}/{report_type}/")
    elapsed_ms = (time.perf_counter() - started) * 1000
    return round(elapsed_ms, 2), response.status_code


def main():
    ctx = create_dataset(
        events_count=8,
        participants_per_event=10,
        tasks_per_event=5,
        orders_per_event=4,
        messages_count=12,
    )

    client = Client()
    client.force_login(ctx.admin)

    main_event_id = ctx.event_ids[0]
    assistant_client = Client()
    assistant_client.force_login(ctx.assistant)
    message_detail_id = ctx.message_ids[0]

    routes = [
        ("home", "/", client),
        ("events", "/events/", client),
        ("event_detail", f"/events/{main_event_id}/", client),
        ("participants", "/participants/", client),
        ("tasks", "/tasks/", client),
        ("expenses", "/expenses/", client),
        ("contractors", "/contractors/", client),
        ("places", "/places/", client),
        ("messages", "/messages/", assistant_client),
        ("message_detail", f"/messages/{message_detail_id}/", assistant_client),
        ("reports", "/reports/", client),
    ]

    try:
        print("PERFORMANCE_RESULTS_START")
        for label, path, route_client in routes:
            result = benchmark_get(route_client, path)
            print(
                f"{label}|{path}|avg={result['avg_ms']}|min={result['min_ms']}|"
                f"max={result['max_ms']}|p95={result['p95_ms']}|status={result['statuses']}"
            )

        original_base_dir = settings.BASE_DIR
        settings.BASE_DIR = Path(settings.BASE_DIR)
        try:
            for report_type in ("event", "expense"):
                elapsed_ms, status_code = benchmark_report_generation(client, main_event_id, report_type)
                print(f"report_{report_type}|ms={elapsed_ms}|status={status_code}")
            ctx.report_ids = list(
                Report.objects.filter(event_id__in=ctx.event_ids).values_list("pk", flat=True)
            )
        finally:
            settings.BASE_DIR = original_base_dir
        print("PERFORMANCE_RESULTS_END")
    finally:
        cleanup_dataset(ctx)


if __name__ == "__main__":
    main()
