# Deferred Phase-3 Cleanups

Date: 2025-01-09

Context: Phase-3 orchestration (runtime loop, worker work execution, persistence)

This note captures deferred, not implemented items that may require a follow-up decision.

1) CmtsOrchestratorRuntime.run_forever docstring should document on_tick_indexed  
Impact: documentation only  
Risk: none

2) Define behavior if both on_tick and on_tick_indexed are provided  
Options: call both (current), or prefer indexed and ignore non-indexed  
Impact: internal API semantics  
Risk: low unless callers rely on double callbacks

3) Remove or use self._mode in CmtsOrchestratorRuntime  
Impact: refactor or lint cleanliness  
Risk: low; ensure not needed for near-term work

4) WorkRunner persistence failure semantics  
Current: log error but still returns SUCCESS  
Potential: mark FAILED on persistence error and use logger.exception for traceback  
Impact: behavior and tests may change  
Risk: medium

5) Expand _sanitize_test_name beyond / and \\  
Impact: filename changes, may affect tests if asserted  
Risk: medium-low
