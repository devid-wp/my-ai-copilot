# Citadex 0.1.0 release

## Files to publish

- `Citadex-0.1.0-windows-x64.zip` — portable Windows release.
- `Citadex-0.1.0-windows-x64.zip.sha256` — checksum for the archive.
- `Citadex.exe` — optional standalone executable for users who do not want the archive.

## GitHub release

1. Push the final commit and tag:

   ```powershell
   git push origin main
   git push origin v0.1.0
   ```

2. Open the repository's **Releases** page and choose **Draft a new release**.
3. Select the existing tag `v0.1.0`.
4. Use the title `Citadex 0.1.0`.
5. Copy the `0.1.0` section from `CHANGELOG.md` into the release description.
6. Attach the three files listed above from the local `dist` directory.
7. Mark the release as a pre-release because `0.1.0` is an alpha.
8. Publish the release.

## Verification for users

Users can verify the archive in PowerShell:

```powershell
Get-FileHash .\Citadex-0.1.0-windows-x64.zip -Algorithm SHA256
```

The result must match the value inside `Citadex-0.1.0-windows-x64.zip.sha256`.

The executable starts with:

```powershell
.\Citadex.exe --version
```

Expected output:

```text
Citadex.exe 0.1.0
```

Windows SmartScreen may warn about an unsigned executable. Code signing is not included in
this release; users should verify the SHA-256 checksum before running the file.
