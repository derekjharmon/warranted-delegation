---
name: tool-conventions
description: Conventions for small research tools written in Python. Use when building a command-line tool.
---

# Conventions for small research tools

- **Interface.** A single script run from the command line, with arguments
  parsed by argparse. Every argument has a help string.
- **Output.** Print results as JSON to standard output, so other programs can
  read them. Errors go to standard error, with a nonzero exit code.
- **Tests.** Use Python's unittest, in a tests/ folder, with at least one test for each
  function and one for each kind of bad input.

Leave everything else to the task.
