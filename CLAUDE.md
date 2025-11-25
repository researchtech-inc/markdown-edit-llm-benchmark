# Rules to follow

- Write elegant code, easy to maintain, easy to understand, without hacks/tricks
- When possible always read full files instead of parts of them
- Before you write any code make sure that the approach you want to use is the best one and that you are not duplicating any code/logic
- Always think hard before you do anything, be sceptical and critical
- Don't implement features you were not asked to do, it includes tests and markdown files with summaries
- The best solution uses least amount of the code, try to come up with solutions like that
- In case of running out of context or context compaction abort execution of current task and wait for user instructions
- Always read CLAUDE.md after compaction, make sure rules from this file stay in context
- Write modern code, only for python 3.12+, don't use old and outdated patterns like for example using Optional which is depreceated since python 3.10
- Don't do not nessecary try catch blocks, imports inside functions, monkeypatching
- Don't create and edit any file unless you are explicitly informed to do it
- Don't use sub-agents unless you are explicitly informed to use them
- Don't add in docstrings, comments and markdown files trivivial and obvious informations. Assume that an experienced senior developer will be reading them
- Don't implement helper functions which have less than three lines of code when it comes to their implementation
- Never use env, if you need to use it then use pydantic-settings

# Code Quality Automation

After any code change, run these commands to verify correctness:

```bash
python -m ruff format .
python -m ruff check .
python -m basedpyright
```

All must pass before considering a change complete.

Key enforcements:
- `typing.Optional` is banned - use `X | None` instead
- `Any` type is banned - commit to real types
- No monkeypatching allowed
- No stray print statements (use rich Console)
- Modern Python 3.12+ syntax enforced via pyupgrade
