"""
Command-line entry points for headless model generation.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


def _load_json(input_path: Path) -> Dict[str, Any]:
    with open(input_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_structure(payload: Dict[str, Any]) -> Tuple[Any, str, Any]:
    from app.models.structure import BuildingRequest, Structure
    from app.utils.hash_utils import calculate_structure_hash

    if "structure" in payload:
        request = BuildingRequest(**payload)
        structure = request.structure
        structure_hash = request.structure_hash or calculate_structure_hash(structure.model_dump())
        return structure, structure_hash, request.component_visibility

    structure = Structure(**payload)
    return structure, calculate_structure_hash(structure.model_dump()), None


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def generate_command(args: argparse.Namespace) -> int:
    from pydantic import ValidationError

    from app.config import settings
    from app.services.model_generator import ModelGenerator
    from app.utils.s3_storage import S3Storage

    settings.ensure_directories()

    input_path = Path(args.input).resolve()
    payload = _load_json(input_path)

    try:
        structure, structure_hash, component_visibility = _parse_structure(payload)
    except ValidationError as exc:
        print(f"Invalid building definition: {exc}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).resolve() if args.output_dir else settings.temp_dir / "cli" / structure_hash
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "manifest.json"
    artifacts = ModelGenerator.generate_glb_artifacts(
        structure=structure,
        output_dir=output_dir,
        structure_hash=structure_hash,
        component_visibility=component_visibility,
    )
    glb_path = artifacts["glb_path"]
    bom_path = artifacts["bom_path"]

    storage = S3Storage(
        bucket_name=args.bucket,
        endpoint_url=args.endpoint_url,
        access_key_id=args.access_key_id,
        secret_access_key=args.secret_access_key,
        region_name=args.region,
        prefix=args.prefix,
    )

    artifact_root = args.artifact_key or structure_hash
    manifest_key = storage.object_key(f"{artifact_root}/manifest.json")
    glb_url = storage.upload_file(glb_path, f"{artifact_root}/model.glb", "model/gltf-binary")
    bom_url = storage.upload_file(bom_path, f"{artifact_root}/bom.json", "application/json")

    manifest = {
        "structure_hash": structure_hash,
        "input": str(input_path),
        "artifacts": {
            "glb": {
                "local_path": str(glb_path),
                "url": glb_url,
            },
            "bom": {
                "local_path": str(bom_path),
                "url": bom_url,
            },
            "manifest": {
                "local_path": str(manifest_path),
                "url": storage.object_url(manifest_key),
            },
        },
    }
    _write_json(manifest_path, manifest)
    storage.upload_file(manifest_path, f"{artifact_root}/manifest.json", "application/json")

    print(json.dumps(manifest, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vine-and-fig",
        description="Generate building model artifacts from JSON definitions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate GLB and BOM artifacts")
    generate.add_argument("input", help="Path to a JSON building definition")
    generate.add_argument("--output-dir", help="Local directory for generated artifacts before upload")
    generate.add_argument("--artifact-key", help="Object-key prefix for this run; defaults to the structure hash")
    generate.add_argument("--bucket", help="S3 bucket name; defaults to S3_BUCKET_NAME")
    generate.add_argument("--endpoint-url", help="S3-compatible endpoint URL; defaults to S3_ENDPOINT_URL")
    generate.add_argument("--access-key-id", help="S3 access key; defaults to S3_ACCESS_KEY_ID")
    generate.add_argument("--secret-access-key", help="S3 secret key; defaults to S3_SECRET_ACCESS_KEY")
    generate.add_argument("--region", help="S3 region; defaults to S3_REGION_NAME")
    generate.add_argument("--prefix", help="Global object-key prefix; defaults to S3_PREFIX")
    generate.set_defaults(func=generate_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
