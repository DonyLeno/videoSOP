# Version History

## v2.3
- **Date**: 2026-02-02
- **Commit Message**: release v2.3 - support time format parsing and add docker build script
- **Description**:
  - Added support for `MM:SS` and `HH:MM:SS` time formats in action parsing to fix display discrepancies.
  - Added `build_docker.sh` script for building and exporting AMD64 Docker images.
  - Ensured MySQL configuration uses `127.0.0.1` and password authentication for container compatibility.

## v2.2
- **Date**: 2026-02-01
- **Commit Message**: chinese version fix chinese name input bug
- **Description**: Fixed an issue where uploading files with Chinese characters in filenames caused errors (ByteString conversion error). Implemented frontend encoding and backend decoding for filenames.
