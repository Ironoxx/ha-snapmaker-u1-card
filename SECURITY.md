# Security policy

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report them privately through GitHub instead:
[Report a vulnerability](https://github.com/Ironoxx/ha-snapmaker-u1-card/security/advisories/new)
(repository → *Security* → *Report a vulnerability*).

Please include what is affected, how to reproduce it and the versions of the
integration, Home Assistant and the printer firmware. You will get an answer
within a few days; a fix is released as soon as it is ready, and you are credited
in the release notes unless you prefer not to be.

## Supported versions

Only the latest release gets security fixes. Update through HACS / the Home
Assistant Marketplace.

## Scope

- The integration `custom_components/snapmaker_u1_card` and its dashboard card.
- Not in scope: the printer firmware (Snapmaker, paxx12), Moonraker, Klipper,
  Spoolman and Home Assistant itself. Please report those to their projects.

The integration talks to the printer and to Spoolman on your local network
without authentication (as Moonraker does by default); keep both out of reach
of the internet.
