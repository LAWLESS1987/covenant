# Succession anchors

Published state roots of the PRIVATE memory store. See [SUCCESSION.md](SUCCESSION.md).

A root is a domain-separated Merkle root over every memory's claim digest. It
reveals nothing about the contents. Anyone holding a copy of the private store
can recompute it and compare. Match means the copy is intact and unaltered;
mismatch means something changed, and the audit chain says where.

To verify a copy you hold:

```
AI_MEMORY_ROOT=/path/to/store python ai_memory_system/main.py verify
```

| date | memories | state root |
|---|---|---|
| 2026-08-30 | 80 | `6bec0168586f764f82a39e59a81c2850c91bbd89f1d819581fe174513922e119` |
