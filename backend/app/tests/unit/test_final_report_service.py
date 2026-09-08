from app.models.final_report import FinalReportResult
from app.services.final_report_service import FinalReportService
from app.simulation.state import WorldState


def test_final_report_is_read_only():
    state = WorldState.create("NORMAL")
    before = (
        state.clock.tick,
        state.environment_version,
        len(state.timeline),
        len(state.sensor_history),
    )

    result = FinalReportService().build_report(state)

    after = (
        state.clock.tick,
        state.environment_version,
        len(state.timeline),
        len(state.sensor_history),
    )

    assert isinstance(result, FinalReportResult)
    assert result.phase == 14
    assert result.total_phases == 14
    assert result.zones == 5
    assert result.roads == 38
    assert result.monitoring_status in {"CLEAR", "STABLE", "ATTENTION"}
    assert after == before


def test_final_report_lists_all_phases():
    state = WorldState.create("NORMAL")
    result = FinalReportService().build_report(state)
    assert [item.phase for item in result.subsystems] == list(range(1, 15))
    assert result.subsystems[-1].name == "Final Integration"
