# Icons (optional)

Drop icon files here to have the packaged app use them:

- `app_icon.ico` - used by the Windows build (`build_windows.bat`, `.spec` file)
- `app_icon.icns` - used by the local macOS build (`build_mac.sh`)

Both builds work without these files; PyInstaller just falls back to its
default icon.
