# KGFS Sample Corpus

This tiny corpus is artificial. It exists so new users can try KGFS without indexing personal files.

Try it in project-local mode:

```bash
kgfs init --project-local
kgfs add-folder "./examples/sample-corpus" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local
kgfs search "op amp gain" --project-local
```

The files do not contain personal data, credentials, logs, databases, caches, or real customer/user material.
