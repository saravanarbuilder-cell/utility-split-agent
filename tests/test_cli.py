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


def test_invalid_config_yaml_returns_2(tmp_path, capsys):
    config = tmp_path / "tenants.yaml"
    config.write_text("method: [\n")

    rc = cli.main(["--amount", "10.00", "--config", str(config)])
    err = capsys.readouterr().err

    assert rc == 2
    assert "invalid YAML in config" in err


def test_empty_config_returns_2(tmp_path, capsys):
    config = tmp_path / "tenants.yaml"
    config.write_text("")

    rc = cli.main(["--amount", "10.00", "--config", str(config)])
    err = capsys.readouterr().err

    assert rc == 2
    assert "config must be a YAML mapping" in err


def test_missing_pdf_returns_2(capsys):
    rc = cli.main(["does-not-exist.pdf", "--config", "config/tenants.example.yaml"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "PDF not found" in err


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
