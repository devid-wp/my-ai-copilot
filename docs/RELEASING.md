# Releasing

1. Update the version in `pyproject.toml`, `core/version.py`,
   `build_local.ps1`, and `CitadexLocalSetup.iss`.
2. Update `CHANGELOG.md`.
3. Run the complete quality checks from `docs/DEVELOPMENT.md`.
4. Build the required artifacts:

   ```powershell
   .\build_exe.bat
   .\build_local.bat
   .\build_installer.bat
   ```

5. Smoke-test the produced executable and installer.
6. Calculate and publish SHA-256 checksums.
7. Commit release metadata, create an annotated version tag, and push both.

Windows SmartScreen may warn about unsigned binaries. Users should download
artifacts only from the official release page and verify the published
checksum.

