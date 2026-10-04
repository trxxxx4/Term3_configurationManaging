@echo off
python src\main.py ^
    --vfs-path "vfs" ^
    --startup-script "tests\startup_error.txt" ^
    --config "config.toml"