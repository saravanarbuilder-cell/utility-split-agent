"""Smoke tests for the CLI wiring — the --amount path needs no key or PDF."""
import cli


def test_amount_path_runs_and_splits(capsys):
    rc = cli.main(["--amount", "247.86", "--config", "config/tenants.example.yaml"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Total: $247.86" in out
    assert "$    99.14" in out  # Tenant One @ 40%


def test_requires_pdf_or_amount(capsys):
    # argparse calls parser.error -> SystemExit(2)
    try:
        cli.main([])
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("expected SystemExit")


def test_missing_config_returns_2(capsys):
    rc = cli.main(["--amount", "10.00", "--config", "config/does_not_exist.yaml"])
    assert rc == 2
