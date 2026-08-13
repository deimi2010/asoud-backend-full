# OpenAPI debt gate

The schema currently contains legacy documentation debt. `drf-spectacular` reports
validation diagnostics but exits successfully, so invoking it directly is not a
sufficient CI gate.

CI runs `scripts/check_openapi.py`. The script generates and validates the schema,
extracts the unique error and warning counts, and compares them with
`config/openapi-baseline.json`.

The build fails when:

- schema generation fails;
- the diagnostic summary cannot be parsed;
- errors or warnings increase; or
- diagnostics decrease without lowering the tracked baseline.

The last condition makes every improvement permanent instead of allowing later
changes to consume the newly created margin.

The error baseline is now zero. The remaining warning baseline covers legacy
operation-id and enum-name collisions and must continue moving monotonically down;
CI rejects any new schema error or warning.
