# MCP Playwright Evaluation Framework

A Pester-based evaluation framework for the `playwright-global` MCP infrastructure across 4 config targets (VS Code, Cursor, Codex, Continue).

## Structure

```
scripts/evaluation/
├── README.md                     ← this file
├── run-evaluation.ps1            ← orchestrator
├── test-helper.psm1              ← shared utilities module
├── infrastructure.Tests.ps1      ← config format, backup/restore, host checks
├── functional.Tests.ps1          ← package verification, dataset-driven tests
├── fixtures/                     ← test fixture config files
│   ├── cursor-mcp-fixture.json
│   ├── codex-config-fixture.toml
│   ├── continue-config-fixture.yaml
│   └── vscode-mcp-fixture.json
├── dataset/
│   └── playwright-eval.jsonl     ← evaluation test dataset
└── results/                      ← generated reports (gitignored)
```

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| PowerShell 5.1+ | any | Script host |
| Pester 5.x | >=5.0.0 | Test framework |
| Python 3.11+ | any | TOML parsing |
| Node.js | >=18 | MCP package |
| npm/npx | any | Package verification |

Install Pester if missing:

```powershell
Install-Module Pester -Force -SkipPublisherCheck -Scope CurrentUser
```

## Usage

```powershell
# Run full evaluation
.\scripts\evaluation\run-evaluation.ps1

# Run only infrastructure tests
.\scripts\evaluation\run-evaluation.ps1 -Tag Infrastructure

# Run only backup/restore round-trip tests
.\scripts\evaluation\run-evaluation.ps1 -Tag RoundTrip

# Run in CI mode (quiet, exit code only)
.\scripts\evaluation\run-evaluation.ps1 -CI

# List available test tags
.\scripts\evaluation\run-evaluation.ps1 -ListTags

# Run Pester directly
Invoke-Pester -Path .\scripts\evaluation\infrastructure.Tests.ps1
Invoke-Pester -Path .\scripts\evaluation\functional.Tests.ps1
```

## Test Groups

| Tag | Scope |
|-----|-------|
| `Infrastructure` | All infrastructure tests |
| `Parsing` | JSON, TOML, YAML config parsing |
| `Comparison` | Desired-state entry matching |
| `RoundTrip` | Backup/restore byte-for-byte verification |
| `Hosts` | Host tool availability |
| `Package` | Package version and CLI verification |
| `Duplicates` | Workspace-level config cleanup check |
| `Fixtures` | Fixture file integrity |
| `Functional` | All functional tests |
| `Dataset` | Dataset-driven evaluation |
| `Scripts` | Integration with existing installer/verifier/rollback |
| `DatasetStructural` | Structural checks from dataset |
| `DatasetFunctional` | Functional checks from dataset |

## Output

- **NUnit XML**: `results/evaluation-results.xml`
- **Markdown report**: `results/evaluation-report.md`
- Compatible with VS Code Test Explorer (Pester extension)

## Adding Tests

1. Add test data to `dataset/playwright-eval.jsonl`
2. Add Pester test blocks to the appropriate `.Tests.ps1` file
3. Tag tests appropriately with `-Tag "YourTag"`
4. Optionally add fixture files to `fixtures/`
