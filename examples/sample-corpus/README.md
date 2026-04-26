# KGFS Sample Corpus

This tiny corpus is artificial. It exists so new users can try KGFS without indexing personal files.

Try it in project-local mode:

```bash
kgfs init --project-local
kgfs add-folder "./examples/sample-corpus" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local
kgfs search "op amp gain" --project-local
kgfs duplicates --project-local
kgfs versions 1 --project-local
```

The corpus includes:

- keyword-search examples such as motor torque and op amp gain
- artificial draft/final version files
- two tiny exact duplicate calibration notes
- a small CSV with fake values

The files do not contain personal data, credentials, logs, databases, caches,
model artifacts, API keys, or real customer/user material.
