# Build and publication checks

Build selected targets without publishing:

```sh
python3 scripts/build.py oc oc-shared sr --no-sync --output-root /tmp/unifom-check
```

The build validates generated structures before writing configurations. Gist
errors and read-back mismatches return a failing exit status. Each configuration
has a `.manifest.json` sidecar with its source commit, version and SHA256.
`content_sha256` excludes the Generated timestamp for meaningful comparisons.
The manifest contains no subscription URLs or configuration body.

OC tag releases install dependencies, build both variants using temporary
credentials, and run Mihomo v1.19.32 configuration checks before uploading.
Provider membership in `scripts/release.py` is the CI release profile; it must
be reviewed when airport membership changes. SR tags validate the tracked
configuration. Stash remains a historical target.

Audit a generated configuration:

```sh
python3 scripts/audit.py /tmp/unifom-check/clash/openclash/dist/UniFOM.yaml --output /tmp/audit.json
python3 scripts/audit.py /tmp/unifom-check/clash/openclash/dist/UniFOM.yaml --remote --output /tmp/audit-remote.json
python3 -m unittest discover -s scripts -p 'test_*.py'
```

Audit generates JSON and text reports. Structural errors stop execution;
overlap findings do not change rules or block publication. An optional
`--exceptions` JSON object maps finding IDs to reviewed explanations.

Coverage is limited to DOMAIN, DOMAIN-SUFFIX, IP-CIDR and IP-CIDR6. Complex,
geodata, wildcard and MRS rules need separate inspection. Remote downloads are
optional; failures and skipped checks are marked incomplete, never as proof
of no conflicts. Reports use rule locations rather than subscription URLs.
