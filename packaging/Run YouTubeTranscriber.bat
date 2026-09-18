@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

if not exist "%SCRIPT_DIR%_internal\python312.dll" (
    mshta "javascript:alert('YouTubeTranscriber cannot start: required files are missing next to this launcher.\n\nThis usually means the ZIP was not extracted first (double-clicking a file straight out of the ZIP preview does not copy the whole folder).\n\nRight-click YouTubeTranscriber-Windows-x64.zip, choose Extract All, then run this file from the extracted folder.');close();"
    exit /b 1
)

start "" "%SCRIPT_DIR%YouTubeTranscriber.exe"
