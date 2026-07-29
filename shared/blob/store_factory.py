from shared.blob.disk_store import DiskStore


def get_store(backend: str, store_path: str):
    if backend == "disk":
        return DiskStore(store_path)
    if backend == "s3":
        raise NotImplementedError("S3 backend is not yet implemented")
    raise ValueError(f"Unknown backend: {backend!r}")
