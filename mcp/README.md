# Synapse MCP Server

This is a Model Context Protocol (MCP) server for Synapse. It allows AI agents (like Claude Desktop) to interact with your Synapse knowledge base.

## Features

*   **Search**: Hybrid search (Text + Semantic) through your items.
*   **Add Memory**: Add notes, URLs, and other items to Synapse.
*   **Read**: Access recent items and item details.

## Prerequisites

*   Synapse Backend running (usually on `http://localhost:8000`)
*   `uv` installed

## Installation

1.  Navigate to this directory:
    ```bash
    cd synapse/mcp
    ```

2.  Install dependencies:
    ```bash
    uv sync
    ```

## Usage with Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synapse": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/synapse/mcp",
        "run",
        "server.py"
      ],
      "env": {
        "SYNAPSE_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/synapse/mcp` with the actual absolute path to this directory.

## Development

To run the MCP inspector for debugging:

```bash
uv run mcp dev server.py
```
