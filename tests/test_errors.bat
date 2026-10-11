@echo off
echo === Stop on the first error of the startup script ===
python src\main.py --config config.toml --vfs-path tests\vfs_nested.xml --startup-script tests\startup_errors.txt
echo.
echo === VFS file not found ===
python src\main.py --config config.toml --vfs-path tests\no_such_file.xml --startup-script tests\startup_ls.txt
echo.
echo === Invalid VFS data ===
python src\main.py --config config.toml --vfs-path tests\vfs_broken.xml --startup-script tests\startup_ls.txt
echo.
echo === Command errors in the interactive mode (input from file) ===
python src\main.py --config config.toml --vfs-path tests\vfs_nested.xml --startup-script tests\startup_ls.txt < tests\repl_errors.txt
