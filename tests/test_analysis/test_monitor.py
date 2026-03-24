from app.workers.monitor import get_pipeline_runs, record_pipeline_run


class TestPipelineMonitor:
    def test_record_run(self):
        record_pipeline_run(
            status="success",
            properties_found=50,
            opportunities_found=3,
            alerts_sent=2,
            duration_seconds=120.5,
        )
        runs = get_pipeline_runs(1)
        assert len(runs) == 1
        assert runs[0]["status"] == "success"
        assert runs[0]["properties_found"] == 50
        assert runs[0]["opportunities_found"] == 3
        assert runs[0]["alerts_sent"] == 2
        assert runs[0]["duration_seconds"] == 120.5
        assert runs[0]["errors"] == []

    def test_record_run_with_errors(self):
        record_pipeline_run(
            status="partial_error",
            properties_found=30,
            errors=["Scraper Yapo falló", "Timeout en API UF"],
            duration_seconds=45.0,
        )
        runs = get_pipeline_runs(1)
        assert runs[0]["status"] == "partial_error"
        assert len(runs[0]["errors"]) == 2

    def test_runs_limit(self):
        for i in range(5):
            record_pipeline_run(
                status="success",
                properties_found=i * 10,
                duration_seconds=float(i),
            )
        runs = get_pipeline_runs(3)
        assert len(runs) <= 3

    def test_runs_ordered_newest_first(self):
        record_pipeline_run(status="old", duration_seconds=1.0)
        record_pipeline_run(status="new", duration_seconds=2.0)
        runs = get_pipeline_runs(2)
        assert runs[0]["status"] == "new"
        assert runs[1]["status"] == "old"
