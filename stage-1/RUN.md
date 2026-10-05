# Run Juniper Tablekeeper — Stage 1

From this directory, build and start the complete, single-container API:

```sh
docker build -t juniper-tablekeeper-stage1 .
docker run --rm --name juniper-stage1 --cpus=2 --memory=2g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -e PORT=8080 -p 8080:8080 juniper-tablekeeper-stage1
```

The image includes Python and IANA timezone data. It binds `0.0.0.0`; `PORT` defaults to `8080`. The service starts with empty state and requires no runtime network or writable filesystem. `GET /health` returns `{"status":"ok"}`. To choose another port, set `PORT` and map that same container port. For a network-isolated check, attach the service and an HTTP test client to a Docker network created with `docker network create --internal`.

`POST /_test/reset` accepts the Stage 1 fixture. Test controls are deliberately unauthenticated. Use synthetic data only. Signup/login return non-expiring bearer tokens. Public reads are `/restaurants`, `/restaurants/{id}` and `/availability`. Authenticated diners can create, list, look up, amend and cancel reservations, and atomically move 1–8 reservations through `/reservation-moves`.

Creation and atomic moves require `Idempotency-Key` (1–255 characters). Preserve the entire request body and key when a response is uncertain. A successful replay returns the original receipt with 200, even if the current reservation changed. Look up the reference to obtain its current state. Rejected writes claim no key.

`GET /_test/export` returns an atomic snapshot; `POST /_test/import` replaces state from that unchanged object. Snapshots include password hashes and live session tokens and must be treated as private test data. No source process or external storage is needed. State is in memory and is lost on container restart unless explicitly exported/imported. Reset clears all data and sessions.

Every response closes its HTTP connection. Standard clients reconnect automatically. Ambiguous framing is rejected before dispatch. The service accepts exact finite JSON numbers without binary rounding and keeps unknown fields in idempotent request identity. Stage 1 is API-only; later-stage UI and domain features are deliberately absent.

For lightweight local developer verification with Python 3.12+, run `python -m unittest discover -s checks -v`. Independent judged-container and frozen-suite results belong to the verifier's evidence, not this command.
