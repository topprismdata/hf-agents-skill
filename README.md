# HF Agents Skill

**A local/private inference access layer for employee coding agents.**

`NATIVE AI` · `INTERNAL UTILITY` · `INTERNAL EVALUATION`

> **Employee capability:** natural-language request → hardware detection
> → compatible local model → local inference server → coding agent.

------------------------------------------------------------------------

## Why this exists

Enterprise Native AI needs more than cloud-model access.

Some employee workflows benefit from:

-   local inference;
-   private data handling;
-   predictable deployment;
-   open-source model choice;
-   offline / constrained environments;
-   hardware-aware model selection.

This repository packages those operational steps into an agent skill.

------------------------------------------------------------------------

## Architecture

``` text
Employee request
      ↓
agent skill
      ↓
hardware detection
      ↓
model compatibility / recommendation
      ↓
model acquisition
      ↓
llama.cpp / local server
      ↓
coding agent
      ↓
status / diagnostics / shutdown
```

------------------------------------------------------------------------

## Positioning

The capability is local / private inference access for employee agents.
Claude Code is one current host interface; the capability itself is
host-agnostic.

------------------------------------------------------------------------

## Evidence

If the README includes a `skill-tester` score, label it explicitly:

> **TopPrism internal skill-quality evaluation**

Do not present the score as an external benchmark.

Likewise, model support and throughput tables should distinguish:

-   measured locally;
-   estimated;
-   upstream-published.

------------------------------------------------------------------------

## Documentation

The README stays stable across model releases. Volatile information
(current supported model list, hardware-specific tuning notes,
troubleshooting recipes) lives in implementation documentation that
ships with the code and is updated independently of this README.

------------------------------------------------------------------------

## Security

Deployment owners must satisfy the following baseline before exposing the
local inference server to other employee agents:

-   downloaded model provenance and license compatibility must be
    reviewed against the company's acceptable-use list;
-   the local server should be bound to the intended network interface;
-   prompt / code privacy must respect the company's data-handling policy;
-   model cache locations and process lifecycle should be cleaned up
    on session boundaries.

------------------------------------------------------------------------

## TopPrism metadata

``` yaml
topprism:
  purpose: native-ai
  capability: local-inference-access
  platform_layer: organizational-intelligence
  maturity: internal-utility
  evidence:
    type: internal-evaluation
```
