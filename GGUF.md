# Optional 2B GGUF

Default realizer is still pure Python.

```bash
pip install llama-cpp-python
export SUE_GGUF=/path/to/2b-instruct-q4_k_m.gguf
python3 sue.py
/model
```

Or drop a `.gguf` in `models/`.
Code, `/eq`, and `/program` stay on the composer.
