Smoke test the operational endpoints end-to-end

Start the API locally and validate the four probes return what you expect:

GET /ops/health

GET /ops/ready (verify 200 vs 503 behavior by mode/state_dir)

GET /ops/version

GET /ops/status (verify pidfiles present/missing and fallback behavior)

This is the one thing unit tests can’t fully guarantee because it exercises the router wiring + runtime env behavior.