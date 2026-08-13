"""Generate OpenAPI and reject regressions against the tracked debt baseline."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SUMMARY_PATTERN = re.compile(
    r"Warnings:\s+\d+\s+\((?P<warnings>\d+) unique\).*?"
    r"Errors:\s+\d+\s+\((?P<errors>\d+) unique\)",
    re.DOTALL,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='schema-ci.yml')
    parser.add_argument('--baseline', default='config/openapi-baseline.json')
    args = parser.parse_args()

    completed = subprocess.run(
        [
            sys.executable,
            'manage.py',
            'spectacular',
            '--file',
            args.output,
            '--validate',
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    diagnostics = f'{completed.stdout}\n{completed.stderr}'
    match = SUMMARY_PATTERN.search(diagnostics)
    if completed.returncode != 0 or match is None:
        sys.stderr.write(diagnostics)
        raise SystemExit('OpenAPI generation failed or did not report diagnostics.')

    actual = {
        'unique_errors': int(match.group('errors')),
        'unique_warnings': int(match.group('warnings')),
    }
    baseline = json.loads(Path(args.baseline).read_text(encoding='utf-8'))
    print(
        'OpenAPI debt: '
        f"{actual['unique_errors']} unique errors, "
        f"{actual['unique_warnings']} unique warnings"
    )

    regressions = [
        name
        for name, value in actual.items()
        if value > int(baseline[name])
    ]
    if regressions:
        sys.stderr.write(diagnostics)
        raise SystemExit(
            'OpenAPI debt increased for: ' + ', '.join(regressions)
        )

    if actual != baseline:
        raise SystemExit(
            'OpenAPI debt improved. Lower config/openapi-baseline.json to make the gain permanent.'
        )


if __name__ == '__main__':
    main()
