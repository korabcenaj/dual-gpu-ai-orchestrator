# Security policy

## Supported version

Security updates are applied to the `main` branch. This demonstration project
does not currently maintain older release branches.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository when
available. If that option is unavailable, contact the repository owner through
the address listed on [korab.space](https://korab.space/) and avoid including
exploit details in a public issue.

Include the affected component, reproduction conditions, likely impact, and any
suggested mitigation. Reports will be acknowledged as availability permits.

## Deployment scope

The Compose configuration is intended for an isolated development host.
Operators are responsible for unique credentials, network policy, TLS, host GPU
permissions, model provenance, and vulnerability review before exposing a
deployment.

One current transitive exception is documented in the README: `diskcache`
5.6.3 is required by `llama-cpp-python` and has an unsafe-deserialization
advisory with no fixed release. This project does not invoke DiskCache APIs.
