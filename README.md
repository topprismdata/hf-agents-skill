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

Do not lead with "Claude Code skill."

The capability is:

> **Local/private inference access for employee agents.**

Claude Code is one current host interface.

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

## Documentation split

Move volatile model lists and hardware-specific recommendations to:

``` text
docs/
├── model-matrix.md
├── hardware.md
├── troubleshooting.md
└── security.md
```

README should stay stable even when model names change.

------------------------------------------------------------------------

## Security

Add guidance for:

-   downloaded model provenance;
-   local server network binding;
-   prompt / code privacy;
-   model license compatibility;
-   cache locations;
-   process cleanup.

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
