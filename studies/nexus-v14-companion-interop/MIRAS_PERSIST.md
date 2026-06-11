# Miras persistence record — cycle 4

## Decision (force: high)
When a reviewer flags a missing capability, the default disposition is IMPLEMENT, not document:
the co-signer attestation gap was closed by minting a real second signature (attending's key
over the author's signature), not by adding a line to the honesty table. Documentation is the
fallback only when implementation is genuinely out of scope.

## Reusable lessons
1. Canonicalization for signatures must be locale-independent (code-unit sort, never
   localeCompare) — collation differences silently break cross-host re-verification.
2. Attestation chains: sign OVER the prior signature so tampering anywhere breaks everything
   downstream (author -> co-signer verified end-to-end).
3. Standards parsers: skip-by-name beats reject-or-coerce for unsupported value types (HL7
   non-NM OBX) — the caller learns exactly what didn't make it in.
4. Commit-flushed journals for the legal record + periodic snapshots for the rest is a clean
   two-tier durability split; stitch-verify on replay, refuse bad stitches.
5. "Zero new dependencies" is a falsifiable claim — have the red-team run npm ls.
6. Session-limit agent kills recurred (2nd cycle running): plan councils with the orchestrator
   able to self-execute any lens checklist; the independent red-team remains the non-negotiable.

source_agent: dev+self-executed-lens+red-team · date: 2026-06-11 · study: nexus-v14-companion-interop
