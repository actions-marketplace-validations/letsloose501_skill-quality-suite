# note-taker

Turns a meeting transcript into a note with decisions and owners.

## Install

```
/plugin marketplace add acme-labs/acme-tools
/plugin install note-taker@acme-old-tools
```

To sync notes between machines, install the companion plugin as well:

```
/plugin install sync-kit@acme-tools
npx skills add acme/sync-kit
```

The transcript format is the one produced by `npx skills add someone-else/transcriber`.
