# Council Paper 2 — Red-Team / QA (gate: PASS WITH CONCERNS → resolved)

Ran all five verification commands (148/148 at attack time; both tsc clean; build clean;
npm ls unchanged — zero-new-deps claim verified). 19 claim verdicts: 18 VERIFIED, 1 OVERCLAIMED.
Notable verifications: cross-user signature test would fail under the v1.3 single-HMAC scheme
(genuinely exercises per-user keys); HL7 MSH-9 indexing recounted by hand; MEWS bands match
Subbe 2001 Table 1 exactly; GAD-7/PHQ-9 wording matches the validated instruments; portal
identity resolution watertight; web-route audit clean.

Findings → dispositions:
- MF-1 (production flag): HL7 import's 404-vs-422 lets upload_labs holders probe MRN existence —
  same hospital-wide trade-off as native lab entry. ACCEPT-WITH-LABEL: README honest label now
  states it explicitly, flagged for production scoping.
- SF-2: README still said "calculators (24)" in three lower sections → fixed to 33.
- SF-3: co-signer attestation lived only in the audit log → FIXED PROPERLY (not documented away):
  cosignNote now mints a SECOND Ed25519 signature with the attending's key OVER the author's
  signature; /verify/note/:id reports cosigned/cosign_valid/cosigner; test proves the chain
  breaks end-to-end when the author signature is tampered. Tests 148 → 149.
