# Contributing

Issues and pull requests are welcome: a false positive on a real skill, a harness whose
documentation moved, a rule that should exist.

## The two rules a change has to keep

- **The static half stays offline, deterministic and standard library only.** Anything
  that needs a model, a network or an API key is an opt-in layer beside it.
- **Every rule ships with a case that has been watched making it fire**, and the `clean/`
  and `escape-hatches/` cases stay silent.

## Before opening a pull request

From the repository root:

```bash
python skills/skill-quality-suite/scripts/sqs.py rules --audit
python tests/run_tests.py
python tests/run_tests.py --coverage
python tools/build_docs.py --check
```

The skill itself is `skills/skill-quality-suite/`. Tests, documentation, tools and CI sit
beside it, not inside it: an installer copies only the skill's folder, and the test
corpus - skills that are broken or malicious on purpose - must never land in a user's
skills directory. Do not put attack-shaped strings into fixture files either; the corpus
assembles them at run time (see `PAYLOADS` in `tests/run_tests.py`).

What each part of the suite expects when you change it is in
[editing-this-suite.md](skills/skill-quality-suite/references/editing-this-suite.md).

## Licence of contributions

SQS is licensed under Apache-2.0. A contribution you submit is licensed under the same
terms (Section 5 of the License), and you add yourself to [CONTRIBUTORS.md](CONTRIBUTORS.md)
in the same pull request.
