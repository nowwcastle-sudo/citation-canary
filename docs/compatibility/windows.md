# Windows portability contract

Citation Canary targets the Windows x64 runner contract described below when
the machine has Python 3.11 or newer. It reads a local HWPX and a local
schema-v1 catalog, makes no network request, and writes reports only to the
operator-selected separate output.

The certification gate runs the same checkout on two clean GitHub-hosted Windows
images: `windows-2022` and `windows-latest`, with Python 3.11 and 3.14 on each.
Each combination runs the complete tests, the zipapp tests, and a fresh
allowlisted build twice and requires identical SHA-256 bytes. The workflow is
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

The build also stages a complete artifact on a different volume when the host
provides one, so a `C:` Python temp directory and a `D:` release directory do
not change the result.

Passing CI for a specific commit provides reproducibility evidence for that
stated OS/runtime contract. Check the run attached to the release commit;
configuration alone is not evidence that a run passed. It
does not claim that an unsupported Python build, a non-UTF-8 catalog, an
institution's source-access policy, or a document outside the tested HWPX
surface has identical behavior. It also does not turn a virtual runner result
into a guarantee about every physical device, filesystem, or enterprise policy.
