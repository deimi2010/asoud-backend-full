# Legacy API artifacts

These files were moved out of the repository root because they are historical
samples, not the authoritative backend contract. Several contain only a small
subset of endpoints and may use old field names or example environments.

The authoritative schema must be generated from the current backend and
validated by CI. Treat every Postman environment as sample input: never place
or retain a real token, OTP, credential, personal identifier, or production
endpoint in these tracked files.

The artifacts are retained for contract archaeology and comparison only:

- `ALL_ENDPOINTS.txt`
- `openapi.yaml`
- `postman_collection.json`
- `ASOUD_API_Complete_Collection_v2.json`
- `ASOUD_API_Complete_Postman_Collection.json`
- `ASOUD_API_Environment.json`
