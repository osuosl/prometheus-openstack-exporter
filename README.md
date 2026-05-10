# Prometheus OpenStack exporter

Exposes high-level [OpenStack](https://www.openstack.org/) metrics to
[Prometheus](https://prometheus.io/). Data can be visualised in
[Grafana](https://grafana.com/) — see the
[OpenStack Clouds Dashboard](https://grafana.com/dashboards/7924) for a
ready-made starting point.

## About this fork

This is the [OSUOSL](https://osuosl.org/) fork of the original
[Canonical project](https://github.com/canonical/prometheus-openstack-exporter),
which is **deprecated upstream**. This fork is maintained for environments
where the upstream replacement isn't a fit.

The default branch is `main`. Bug fixes and small enhancements are accepted;
larger architectural changes (asyncio migration, openstacksdk migration) are
not currently planned.

## Installation

### From RPM (recommended for RHEL/AlmaLinux)

The companion repo at
[osuosl/openstack_exporter](https://gitlab.osuosl.org/osl/rpms/openstack_exporter)
builds RPMs for AlmaLinux 9 / 10 with OpenStack release-pinned dependencies
via upper-constraints. The RPM ships a self-contained venv under
`/opt/openstack_exporter/` plus the systemd unit and config defaults.

### From source

```sh
python3 -m venv /opt/prometheus-openstack-exporter
/opt/prometheus-openstack-exporter/bin/pip install -r requirements.txt .
```

For a specific OpenStack release, use that release's upper-constraints:

```sh
/opt/prometheus-openstack-exporter/bin/pip install \
  -c https://opendev.org/openstack/requirements/raw/tag/yoga-eom/upper-constraints.txt \
  -r requirements.txt .
```

## Configuration

Two files drive the exporter at runtime:

1. **`/etc/prometheus-openstack-exporter/prometheus-openstack-exporter.yaml`** —
   exporter behavior (refresh interval, swift hosts, allocation ratios, etc.).
   Options are documented inline in
   [`prometheus-openstack-exporter.sample.yaml`](prometheus-openstack-exporter.sample.yaml).

2. **`/etc/prometheus-openstack-exporter/admin.novarc`** — OpenStack credentials
   sourced into the service environment. Modern (Keystone v3) example:

   ```sh
   export OS_IDENTITY_API_VERSION=3
   export OS_AUTH_URL=https://keystone.example.com:5000/v3
   export OS_USERNAME=admin
   export OS_PASSWORD=XXXX
   export OS_PROJECT_NAME=admin
   export OS_USER_DOMAIN_NAME=Default
   export OS_PROJECT_DOMAIN_NAME=Default
   export OS_REGION_NAME=RegionOne
   ```

   For legacy v2 deployments, set `OS_IDENTITY_API_VERSION=2` and use
   `OS_TENANT_NAME` instead of `OS_PROJECT_NAME`. Empty/unset
   `OS_IDENTITY_API_VERSION` defaults to v2.

`/etc/default/prometheus-openstack-exporter` should set `CONFIG_FILE` to the
yaml path.

## Running

### systemd

```sh
sudo cp prometheus-openstack-exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now prometheus-openstack-exporter
```

### Interactively

```sh
. /etc/prometheus-openstack-exporter/admin.novarc
./prometheus-openstack-exporter /etc/prometheus-openstack-exporter/prometheus-openstack-exporter.yaml
```

Metrics are served at `http://<host>:9183/metrics`.

## Operational behavior

- **Cache-backed scrapes.** A background `DataGatherer` thread polls
  OpenStack on a configurable `refresh_interval` and writes a pickle to
  `/var/cache/prometheus-openstack-exporter/cache`. `/metrics` reads that
  cache instead of hitting OpenStack on every scrape — necessary because
  the underlying queries can take minutes on larger clouds.
- **Startup window.** Until the gatherer writes its first cache (a few
  seconds after start), `/metrics` returns HTTP `503 Service Unavailable`
  with a clear message. Prometheus will mark `up=0` for that brief window;
  this is intentional and lets you alert on persistent 503s.
- **Cache age.** The metric `openstack_exporter_cache_age_seconds` reports
  how stale the cache is. Alert on this rather than on scrape latency.

## FAQ

### Why are openstack_allocation_ratio values hardcoded?

There's no OpenStack API to retrieve them. Hardcoding them in queries (the
alternative) breaks when ratios change.

### Why hardcode the swift host list?

Same reason — no API to enumerate them.

### Why not write a dedicated Swift exporter?

Swift stats are included because they're trivial to retrieve from the rings.
If a standalone Swift exporter appears we can revisit.

### Why cache data?

Prometheus best-practice is to avoid caching, but the OpenStack queries we
run are heavy — multiple servers scraping uncached would impact cloud
performance. The cache decouples scrape cadence from API call cadence.

### How are Swift account metrics obtained?

Given the Swift rings (`account.ring.gz` is enough), the exporter asks the
ring where a particular account lives, picks a node at random, and issues
an HTTP HEAD to that node's account server.

### How hard would it be to export Swift usage by container?

Doable: GET the account URL for a (paginated) container list, then use
`container_ring.get_nodes(account, container)` + HTTP HEAD on one of the
resulting nodes. Without caching cleverness it will scale poorly.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Tests:

```sh
venv/bin/python -m unittest discover tests
tox -e lint
```
