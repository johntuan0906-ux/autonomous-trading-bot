# GitHub Copilot Custom Instructions — Autonomous Trading Bot

## Core Project Architecture & Stack
- **Project Domain**: Autonomous 100% USDT-M Binance Futures Trading Bot & AI Memory System (`memory-graph` / `openbrain`).
- **Target Pairs**: BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT.
- **Strategy & Execution**: Single Best Setup via Composite Alpha Score (Technical Momentum 65% + Macro Sentiment 35%), R:R = 1:2 (SL 1.5×ATR, TP 3×ATR), Risk per trade = 1%, Kill-switch protection.
- **Python Runtime**: Windows PowerShell environment. Use explicit Python path when running scripts: `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`.

## Code Analysis & Knowledge Graph First
- **Before reading/grepping large files or codebases**, leverage the embedded OpenBrain/Memory Graph tools for fast context retrieval:
  - Query project context: `python memory_agent.py context "<query>"`
  - Get project architecture: `python memory_agent.py arch`
  - Search graph database: `python memory_graph.py search --query <query>`
  - Trace call paths: `python memory_agent.py trace <start_node>`
  - Get snippet context: `python memory_agent.py snippet <node_id>`

## Key Project Rules & Conventions
1. **Context & Reading**:
   - Do not re-read files already loaded in memory.
   - Read specific line ranges for files larger than 300 lines.
   - Limit search regexes to specific symbols.

2. **Edits & Output**:
   - Make minimal, targeted edits (prefer `replace_string_in_file`).
   - Do not print full code files in responses unless requested.
   - Keep responses concise, actionable, and structured with short bullet points.

3. **Verification**:
   - Run verification tests on edited modules using specific Python test subsets:
     `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe -m unittest tests/test_<module>.py`
   - Check compilation before concluding: `python -m py_compile <modified_file.py>`

4. **Environment Execution (Windows / PowerShell)**:
   - Always use semicolon `;` to separate commands; **NEVER** use `&&` or `||` in PowerShell.
   - Python path variable: `$py="C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe"`
   - Output redirection: Use `2>$null` or redirect stdout/stderr to separate files when backgrounding processes.

5. **Memory Graph Logging**:
   - Record significant errors or fixes: `python memory_graph.py observe --kind error --sym <symbol> --detail "<cause + fix>"`
   - Sync graph after structural changes: `python memory_agent.py sync`
   - Whenever source code, indexed knowledge, or map input data changes, identify the affected graph/index/maps and update or rebuild them before finishing. At minimum run `python memory_agent.py sync` after source/structure changes; refresh generated map data/visualizations (for example `memory_map.py`, `graph_memory.py`, or Glow map builders) only when their source data or generator inputs changed. Verify the resulting artifacts are current; do not treat trading-market/runtime data as source-code graph data.
