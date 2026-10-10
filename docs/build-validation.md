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

## Runtime DNS leak check after each configuration change

The agent must open https://ipleak.net in a browser on a device running the
new configuration, or routed through the target OpenClash router. Wait for
DNS detection to finish and use a fresh tab after reconnecting. A web-search
fetch or CI runner does not exercise the target device's DNS path.

Record the configuration version, client, network, selected node, browser
secure-DNS setting, observed public exit and resolver ownership. Compare the
resolvers with the intended DNS policy. Unexpected ISP resolvers require
investigation; resolver country or a resolver IP different from the proxy
exit is not sufficient evidence of a leak. Domestic direct DNS and proxy
bootstrap queries may be intentional and are outside this website's complete
coverage. Browser secure DNS can bypass the system resolver, so results apply
only to the tested browser and network state.

Report passed, failed or unverified with evidence. Do not report success if
the device is inaccessible, detection remains pending or the resolver path
cannot be determined. Record IPv6/WebRTC results separately from DNS results.
Do not publish raw IP addresses or node credentials in repository reports.
