#!/usr/bin/env python3
"""Build and publish the Gety custom-connector v2 test releases.

Usage: publish.py <build|publish> <sandbox|fullaccess>
"""

import copy
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER = "yuche"

BASE_FIELDS = [
    {
        "id": "folder",
        "title": "Folder",
        "type": "directory",
        "description": "Index the .txt files in this folder.",
    },
    {
        "id": "probe_denied",
        "title": "Probe httpbin.org",
        "type": "checkbox",
        "description": "Fetch httpbin.org, which is granted from 1.2.0 on.",
        "default_value": False,
    },
]
LABEL_FIELD = {
    "id": "label",
    "title": "Label",
    "type": "text",
    "description": "Required from 2.0.0 on.",
    "required": True,
}


def sandbox_manifest(version):
    major_minor = tuple(int(part) for part in version.split("-")[0].split(".")[:2])
    net = ["example.com"]
    if major_minor >= (1, 2):
        net.append("httpbin.org")
    fields = copy.deepcopy(BASE_FIELDS)
    manifest = {
        "id": "gety_test_sandbox",
        "name": "Gety Test Sandbox",
        "version": version,
        "min_gety_app_version": "0.7.0",
        "capabilities": ["data-source"],
        "entry": "main.js",
        "description": f"Sandboxed test connector for custom connector v2 ({version}).",
        "author": {"name": "yuche"},
        "schedule": {"strategy": "interval", "interval_seconds": 3600},
        "doc_link": {"kind": "file", "field": "path"},
        "permissions": {"net": net, "read": [{"config_field": "folder"}]},
    }
    if major_minor >= (2, 0):
        fields.append(LABEL_FIELD)
        manifest["sync_version"] = 2
    if version == "3.0.0":
        manifest["min_gety_app_version"] = "99.0.0"
    manifest["config"] = {"fields": fields}
    prefix = "v2:" if major_minor >= (2, 0) else ""
    return manifest, prefix


def fullaccess_manifest(version):
    return {
        "id": "gety_test_fullaccess",
        "name": "Gety Test Full Access",
        "version": version,
        "min_gety_app_version": "0.7.0",
        "capabilities": ["data-source"],
        "entry": "main.js",
        "description": "Unrestricted test connector for custom connector v2.",
        "author": {"name": "yuche"},
        "schedule": {"strategy": "interval", "interval_seconds": 3600},
        "doc_link": {"kind": "url", "field": "url"},
        "permissions": "unrestricted",
    }, ""


CONNECTORS = {
    "sandbox": {
        "repo": "gety-test-sandbox-connector",
        "manifest": sandbox_manifest,
        # (version, prerelease)
        "releases": [
            ("1.0.0", False),
            ("1.1.0", False),
            ("1.2.0", False),
            ("2.0.0", False),
            ("2.1.0-beta.1", True),
            ("3.0.0", False),
        ],
    },
    "fullaccess": {
        "repo": "gety-test-fullaccess-connector",
        "manifest": fullaccess_manifest,
        "releases": [("1.0.0", False)],
    },
}


def build(kind, version):
    spec = CONNECTORS[kind]
    manifest, prefix = spec["manifest"](version)
    out = os.path.join(HERE, "dist", kind, version)
    os.makedirs(out, exist_ok=True)
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    with open(os.path.join(HERE, kind, "main.js")) as source:
        code = source.read().replace("__VERSION__", version)
        code = code.replace("__DOC_PREFIX__", prefix)
    manifest_path = os.path.join(out, "manifest.json")
    with open(manifest_path, "wb") as file:
        file.write(manifest_bytes)
    zip_path = os.path.join(out, f"{manifest['id']}-{version}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("main.js", code)
    return manifest_path, zip_path


def publish(kind):
    spec = CONNECTORS[kind]
    repo = f"{OWNER}/{spec['repo']}"
    for version, prerelease in spec["releases"]:
        manifest_path, zip_path = build(kind, version)
        args = ["gh", "release", "create", f"v{version}", manifest_path, zip_path,
                "--repo", repo, "--title", f"v{version}",
                "--notes", f"Test release {version}."]
        if prerelease:
            args.append("--prerelease")
        subprocess.run(args, check=True)


if __name__ == "__main__":
    action, kind = sys.argv[1], sys.argv[2]
    if action == "build":
        for version, _ in CONNECTORS[kind]["releases"]:
            print(*build(kind, version))
    else:
        publish(kind)
