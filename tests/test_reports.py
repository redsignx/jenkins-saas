"""
Unit tests for the report renderer.
"""
import io
import pytest

from src.reports import render_text, render_csv, CSV_HEADERS


class TestTextRenderer:
    def test_header_present(self, annual_report):
        buf = io.StringIO()
        render_text(annual_report, buf)
        out = buf.getvalue()
        assert "Jenkins SaaS Annual Billing Report" in out
        assert "2025" in out

    def test_all_teams_present(self, annual_report):
        buf = io.StringIO()
        render_text(annual_report, buf)
        out = buf.getvalue()
        for tr in annual_report.team_reports:
            assert tr.team_name in out

    def test_grand_total_present(self, annual_report):
        buf = io.StringIO()
        render_text(annual_report, buf)
        out = buf.getvalue()
        assert "GRAND TOTAL" in out


class TestCsvRenderer:
    def test_csv_has_header(self, annual_report):
        buf = io.StringIO()
        render_csv(annual_report, buf)
        lines = buf.getvalue().splitlines()
        assert lines[0] == ",".join(CSV_HEADERS)

    def test_csv_row_count(self, annual_report):
        buf = io.StringIO()
        render_csv(annual_report, buf)
        lines = buf.getvalue().splitlines()
        expected_lines = sum(len(tr.line_items) for tr in annual_report.team_reports)
        # header + data rows
        assert len(lines) == expected_lines + 1

    def test_csv_team_names_present(self, annual_report):
        buf = io.StringIO()
        render_csv(annual_report, buf)
        content = buf.getvalue()
        for tr in annual_report.team_reports:
            assert tr.team_name in content
