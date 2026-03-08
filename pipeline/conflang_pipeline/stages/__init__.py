"""
Pipeline stages for processing Conference talks.

Each stage is a separate module that:
1. Validates its inputs
2. Processes the data
3. Writes outputs with a manifest
4. Returns success/failure

Stages are designed to be idempotent and resumable.
"""
