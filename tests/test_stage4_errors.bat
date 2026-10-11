@echo off
echo ===== ls =====
python src\main.py --config config.toml --vfs-path tests\vfs_student.xml ^
--startup-script tests\stage4\startup_err_ls.txt
echo.
echo ===== cd =====
python src\main.py --config config.toml --vfs-path tests\vfs_student.xml ^
--startup-script tests\stage4\startup_err_cd.txt
echo.
echo ===== find =====
python src\main.py --config config.toml --vfs-path tests\vfs_student.xml ^
--startup-script tests\stage4\startup_err_find.txt
echo.
echo ===== tac =====
python src\main.py --config config.toml --vfs-path tests\vfs_student.xml ^
--startup-script tests\stage4\startup_err_tac.txt
echo.
