# Veritas MCP Server

MCP server that exposes Veritas KYC/AML endpoints as tools for AI agents (Claude, etc.).

## Installation

```bash
cd packages/veritas-mcp
pip install -e .
# or
uv pip install -e .
```

## Configuration

Set the following environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VERITAS_API_KEY` | Yes | — | Your Veritas API key (`vrt_sk_...`) |
| `VERITAS_API_URL` | No | `https://veritas-api.onrender.com/v1` | API base URL including `/v1` |

## Usage

```bash
# Run directly
veritas-mcp

# Or as a module
python -m veritas_mcp
```

### Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "veritas": {
      "command": "python",
      "args": ["-m", "veritas_mcp"],
      "env": {
        "VERITAS_API_URL": "https://veritas-api.onrender.com/v1",
        "VERITAS_API_KEY": "vrt_sk_your_key_here"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `verify_identity` | Upload a document for async KYC processing |
| `run_kyc_process` | Full KYC in one call (OCR + sanctions + risk) — under 15s |
| `get_document_status` | Poll processing status after upload |
| `get_kyc_results` | Get complete KYC results for a customer |
| `check_sanctions` | Screen a name against OFAC/EU/UN sanctions lists |
| `get_statistics` | Get account usage statistics |

## Development

```bash
uv sync --all-extras
uv run pytest
```
