@echo off
python src\main.py ^
    --vfs-path "custom_vfs" ^
    --startup-script "tests\startup.txt" ^
    --config "config.toml"