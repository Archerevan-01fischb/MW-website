@echo off
net use Y: /delete /y 2>nul
net use Y: \\10.0.0.55\midwinter /user:fischb Arch3rD0g6074 /persistent:yes
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Y: drive reconnected to \\10.0.0.55\midwinter
) else (
    echo FAILED: Could not connect. Error code: %ERRORLEVEL%
)
pause
