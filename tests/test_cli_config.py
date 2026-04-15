import pytest

from ai_translator import (
    ClaudeCLIProvider,
    HTTPProvider,
    build_arg_parser,
    create_provider_from_args,
    main,
)


def test_build_arg_parser_reads_provider_env_defaults(monkeypatch):
    monkeypatch.setenv("AI_TRANSLATOR_PROVIDER", "http")
    monkeypatch.setenv("AI_TRANSLATOR_PROTOCOL", "openai")
    monkeypatch.setenv("AI_TRANSLATOR_MODEL", "user.gemma-4-26B-A4B-it-GGUF")
    monkeypatch.setenv("AI_TRANSLATOR_BASE_URL", "http://localhost:13305/v1")
    monkeypatch.setenv("AI_TRANSLATOR_API_KEY", "example-api-key")
    monkeypatch.setenv("AI_TRANSLATOR_TIMEOUT", "99")

    args = build_arg_parser().parse_args(["測試"])

    assert args.provider == "http"
    assert args.protocol == "openai"
    assert args.model == "user.gemma-4-26B-A4B-it-GGUF"
    assert args.base_url == "http://localhost:13305/v1"
    assert args.api_key == "example-api-key"
    assert args.timeout == 99


def test_build_arg_parser_falls_back_when_timeout_env_is_invalid(monkeypatch):
    monkeypatch.setenv("AI_TRANSLATOR_TIMEOUT", "not-an-int")

    args = build_arg_parser().parse_args(["測試"])

    assert args.timeout == 120


def test_create_provider_from_args_defaults_to_claude():
    args = build_arg_parser().parse_args(["測試"])
    provider = create_provider_from_args(args)

    assert isinstance(provider, ClaudeCLIProvider)


def test_create_provider_from_args_builds_http_provider():
    args = build_arg_parser().parse_args([
        "--provider",
        "http",
        "--protocol",
        "anthropic",
        "--base-url",
        "http://localhost:13305",
        "--model",
        "user.gemma-4-26B-A4B-it-GGUF",
        "--api-key",
        "example-api-key",
        "--timeout",
        "55",
        "測試",
    ])
    provider = create_provider_from_args(args)

    assert isinstance(provider, HTTPProvider)
    assert provider.protocol == "anthropic"
    assert provider.model_name == "user.gemma-4-26B-A4B-it-GGUF"
    assert provider.endpoint_fingerprint == "anthropic|http://localhost:13305"


def test_create_provider_from_args_requires_http_base_url():
    args = build_arg_parser().parse_args([
        "--provider",
        "http",
        "--model",
        "user.gemma-4-26B-A4B-it-GGUF",
        "測試",
    ])

    with pytest.raises(ValueError, match="--base-url"):
        create_provider_from_args(args)



def test_create_provider_from_args_requires_http_model():
    args = build_arg_parser().parse_args([
        "--provider",
        "http",
        "--base-url",
        "http://localhost:13305/v1",
        "測試",
    ])

    with pytest.raises(ValueError, match="--model"):
        create_provider_from_args(args)



def test_main_exits_with_parser_error_for_invalid_http_config(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main([
            "--provider",
            "http",
            "--base-url",
            "http://localhost:13305/v1",
            "測試",
        ])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "--model" in captured.err
