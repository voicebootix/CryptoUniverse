from app.services.system_monitoring import MetricsCollector


def test_metric_summary_includes_trend_and_percentiles():
    collector = MetricsCollector(max_points=10)
    collector.record_metric("cpu_usage_pct", 10.0)
    collector.record_metric("cpu_usage_pct", 12.0)
    collector.record_metric("cpu_usage_pct", 15.0)

    summary = collector.get_metric_summary("cpu_usage_pct", duration_minutes=5)

    assert summary["trend"] == "increasing"
    assert "p95" in summary
    assert summary["p95"] >= summary["median"]
    assert summary["change_pct"] is not None
