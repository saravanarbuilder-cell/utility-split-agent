"""Smoke tests for the CLI wiring — the --amount path needs no key or PDF."""
import json

import cli


def test_amount_path_runs_and_splits(capsys):
    rc = cli.main(["--amount", "247.86", "--config", "config/tenants.example.yaml"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Total: $247.86" in out
    assert "$    99.14" in out  # Tenant One @ 40%


def test_amount_path_can_print_json(capsys):
    rc = cli.main([
        "--amount",
        "247.86",
        "--config",
        "config/tenants.example.yaml",
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["config_path"] == "config/tenants.example.yaml"
    assert payload["method"] == "fixed_percent"
    assert payload["total"] == "247.86"
    assert payload["charges"][0]["amount"] == "99.14"


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


def test_list_providers(capsys):
    rc = cli.main(["--list-providers"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "example" in out


def test_fetch_unknown_provider_returns_2(capsys):
    rc = cli.main(["--fetch", "nope", "--config", "config/tenants.example.yaml"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Unknown provider" in err
