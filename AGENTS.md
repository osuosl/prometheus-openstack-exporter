# Agent guidance for prometheus-openstack-exporter (OSUOSL fork)

## What this is

A single-file Python 3 daemon (`prometheus-openstack-exporter`, ~1100 lines)
that scrapes OpenStack APIs and exposes Prometheus metrics on `:9183/metrics`.
Originally a Canonical project, **deprecated upstream**. This OSUOSL fork is
being maintained for environments where the upstream replacement isn't a fit.

The default branch is `main` (upstream's was `master`). PRs back to upstream
are unlikely to be merged.

## Companion repo

The RPM build pipeline lives in a separate repo, typically at
`/home/lance/git/rpms/openstack_exporter` on a dev machine. Cross-cutting
work (a runtime fix that surfaces as a packaging crash) usually means a code
change here and an iteration bump there.

## Repo layout

| Path                                      | What it is                                  |
| ----------------------------------------- | ------------------------------------------- |
| `prometheus-openstack-exporter`           | The main script (no `.py` extension).       |
| `prometheus_openstack_exporter.py`        | Symlink to the script — needed for `tests/` to `import` it. |
| `tests/test_poe.py`, `test_SwiftAccountUsage.py` | Unit tests (`unittest` + `mock`).    |
| `prometheus-openstack-exporter.service`   | systemd unit (sources `/etc/prometheus-openstack-exporter/admin.novarc`). |
| `prometheus-openstack-exporter.yaml`      | Sample config installed to `/etc/`.         |
| `pyproject.toml` / `tox.ini`              | Lint config: black, isort, flake8.          |
| `Makefile`                                | `make test`, `make lint`, `make build`.     |

## How to run things

```sh
# Tests (use the project venv, not system python)
venv/bin/python -m unittest discover tests

# Lint (matches CI semantics)
tox -e lint

# Project flake8 max-line-length is 99, NOT 79 — set in pyproject.toml.
venv/bin/python -m flake8 --max-line-length=99 prometheus-openstack-exporter
```

`tox -e lint` will report pre-existing black/isort drift in unrelated
regions (an artifact of newer formatter versions vs. older committed
code). Do not "fix" those drifts incidentally — touch only what your
change requires.

## Architecture in two paragraphs

The script monkey-patches with `eventlet` at import time, then defines
collector classes (`Nova`, `Neutron`, `Cinder`, `Swift`, `SwiftAccountUsage`,
`SwiftRecon`) plus a `DataGatherer` thread. The gatherer authenticates to
OpenStack on a `refresh_interval` loop and writes a pickle of all queryable
state to `/var/cache/prometheus-openstack-exporter/cache`. The HTTP handler
(`OpenstackExporterHandler.do_GET`) instantiates the configured collectors
on each `/metrics` scrape; each collector's `__init__` reads that cache
file and converts it to Prometheus metrics.

This split exists because Nova/Neutron/Cinder API calls are slow and
unsuitable for synchronous scrape latency. The cache decouples scrape
cadence from API-call cadence, at the cost of a startup window where
the cache doesn't yet exist (the handler returns HTTP 503 in that window —
intentional, see `do_GET`).

## Things that will bite you

- **Eventlet import order is load-bearing.** `eventlet.patcher.monkey_patch()`
  must run before any other imports. That's why every other import is
  preceded by `# noqa: E402`. Do not rearrange.
- **Tests `import prometheus_openstack_exporter`** via the symlink. If the
  symlink is broken or the script has a top-level error (e.g. broken
  imports), test discovery fails with a confusing `ModuleNotFoundError`.
- **Cache-file dependency.** Each of `Neutron.__init__`, `Cinder.__init__`,
  `Nova.__init__` opens `config["cache_file"]`. If the gatherer hasn't
  written it yet, they raise `FileNotFoundError`. The handler catches this
  and returns 503; do not paper over that with a `try/except` inside the
  collectors.
- **Keystone v2 vs v3 branching** lives in `get_clients()` and keys off
  `OS_IDENTITY_API_VERSION`. Empty-string is treated as "unset" (an empty
  env var would otherwise crash `int("")`). Modern deployments need
  `OS_IDENTITY_API_VERSION=3`; the v2 path requires the legacy
  `OS_TENANT_NAME` which v3 deployments don't set.
- **`self.wfile.write(...)` requires bytes.** The HTTP handler's error
  paths used to write a `str` — that's been fixed, do not reintroduce.
- **Don't add `configparser==3.5` or `simplejson<3.17`** to
  `requirements.txt`. Both were old workarounds and have been removed
  deliberately.

## Deprecation context

- `eventlet` itself is now deprecated (DeprecationWarning at startup).
  Migrating away (asyncio) is a substantial rewrite — out of scope for
  bug-fix work.
- `python-neutronclient` bindings are deprecated in favor of
  `openstacksdk`. Same answer: out of scope unless explicitly requested.

## When in doubt

- `git log` in this repo and the companion RPM repo carry the most
  authoritative recent context.
- The `/metrics` endpoint and the cache file are the two main contracts;
  preserve both unless there's a deliberate reason to break them.
