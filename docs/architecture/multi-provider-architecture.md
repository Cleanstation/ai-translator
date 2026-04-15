# Multi-Provider Architecture

## Overview

`ai-translator` started as a translation workflow wrapped around `claude --print`.
It now supports multiple model backends while preserving the same translation-oriented CLI and Python API.

The design goal is simple:
- keep the translation workflow stable
- make the model backend pluggable
- keep the public interface safe and generic

## Core responsibilities

`Translator` remains responsible for:
- collecting context
- building prompts
- formatting output
- cache orchestration
- CLI / Python API integration

Provider implementations are responsible for:
- sending prompts to a model backend
- returning raw model text
- surfacing transport/runtime errors clearly

## Current provider model

### Claude CLI provider

`ClaudeCLIProvider` preserves the original behavior:
- shells out to `claude --print`
- keeps existing usage viable
- acts as the default provider when no explicit provider is configured

### HTTP provider

`HTTPProvider` supports two protocol modes:
- OpenAI-compatible
- Anthropic-compatible

The provider is configured through CLI flags or `AI_TRANSLATOR_*` environment variables.

## Parsing model output

Model output is parsed through dedicated helpers instead of inline regex-only extraction.
The parsing flow is:
1. direct JSON object parse
2. fenced JSON block parse
3. embedded JSON object extraction
4. explicit error if no valid translation object is found

This keeps transport logic and response parsing separate.

## Cache design

Cache entries are separated by dimensions that materially affect output:
- provider
- model
- endpoint fingerprint
- output format
- max length
- prompt version
- context digest
- source text

This avoids cache pollution across providers, models, and endpoints.

## Public-repo rule

This repository intentionally documents only generic/public-safe integration examples.
Real hostnames, private downstream repo details, and secret paths belong in machine-local configuration or private notes, not in the public repo.
