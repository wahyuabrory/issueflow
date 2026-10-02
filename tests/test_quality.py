import subprocess
import sys
from pathlib import Path

import duckdb


def test_quality_passes_for_valid_data(tmp_path):
    db_path = tmp_path / "issueflow.duckdb"

    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE issues (
            id BIGINT,
            repo VARCHAR,
            number INTEGER,
            title VARCHAR,
            state VARCHAR,
            created_at VARCHAR,
            updated_at VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO issues
        VALUES (
            1,
            'owner/repo',
            1,
            'Test issue',
            'open',
            '2026-01-01',
            '2026-01-02'
        )
    """)

    con.execute("""
        CREATE TABLE classifications (
            issue_id BIGINT,
            issue_type VARCHAR,
            confidence DOUBLE,
            issue_updated_at VARCHAR,
            classifier_version VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO classifications
        VALUES (
            1,
            'bug',
            0.9,
            '2026-01-02',
            'v2'
        )
    """)

    con.close()

    script = (
        Path(__file__).parents[1]
        / "src"
        / "issueflow"
        / "quality.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "1 / 1 (100.00%)" in result.stdout
    assert "All quality checks passed" in result.stdout


def test_quality_fails_for_invalid_issue_state(tmp_path):
    db_path = tmp_path / "issueflow.duckdb"

    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE issues (
            id BIGINT,
            repo VARCHAR,
            number INTEGER,
            title VARCHAR,
            state VARCHAR,
            created_at VARCHAR,
            updated_at VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO issues
        VALUES (
            1,
            'owner/repo',
            1,
            'Test issue',
            'invalid',
            '2026-01-01',
            '2026-01-02'
        )
    """)

    con.execute("""
        CREATE TABLE classifications (
            issue_id BIGINT,
            issue_type VARCHAR,
            confidence DOUBLE,
            issue_updated_at VARCHAR,
            classifier_version VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO classifications
        VALUES (
            1,
            'bug',
            0.9,
            '2026-01-02',
            'v2'
        )
    """)

    con.close()

    script = (
        Path(__file__).parents[1]
        / "src"
        / "issueflow"
        / "quality.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "FAIL  Invalid issue states: 1" in result.stdout
    assert "Quality checks failed: 1" in result.stdout

def test_quality_fails_for_stale_classification(tmp_path):
    db_path = tmp_path / "issueflow.duckdb"

    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE issues (
            id BIGINT,
            repo VARCHAR,
            number INTEGER,
            title VARCHAR,
            state VARCHAR,
            created_at VARCHAR,
            updated_at VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO issues
        VALUES (
            1,
            'owner/repo',
            1,
            'Test issue',
            'open',
            '2026-01-01',
            '2026-01-03'
        )
    """)

    con.execute("""
        CREATE TABLE classifications (
            issue_id BIGINT,
            issue_type VARCHAR,
            confidence DOUBLE,
            issue_updated_at VARCHAR,
            classifier_version VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO classifications
        VALUES (
            1,
            'bug',
            0.9,
            '2026-01-02',
            'v2'
        )
    """)

    con.close()

    script = (
        Path(__file__).parents[1]
        / "src"
        / "issueflow"
        / "quality.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "FAIL  Stale V2 classifications: 1" in result.stdout