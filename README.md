# Эмулятор командной оболочки

## Общее описание

Консольный эмулятор UNIX-подобной командной оболочки,
реализованный на Python (версия 3.11 или новее, используются
только стандартные библиотеки).

Эмулятор работает с виртуальной файловой системой (VFS),
которая загружается из XML-файла и целиком хранится в памяти.
Содержимое файлов в XML записывается в формате Base64.
Исходный XML-файл никогда не изменяется: все модификации VFS
(например, команда `touch`) выполняются только в памяти и
пропадают при завершении программы.

Этапы разработки:

1. REPL: приглашение вида `username@hostname:~$`, разбор
   аргументов в кавычках, обработка ошибок, команда `exit`.
2. Конфигурация: параметры командной строки, TOML-файл,
   стартовый скрипт, останавливающийся на первой ошибке.
3. VFS: загрузка файловой системы из XML (Base64) в память.
4. Основные команды: `ls` (флаги `-a`, `-l`, `-h`), `cd`,
   `find`, `tac`.
5. Дополнительные команды: `touch`, `help`.

## Структура проекта

* `src/main.py` — точка входа, конфигурация, REPL, стартовый скрипт;
* `src/vfs.py` — загрузка VFS из XML и операции над ней в памяти;
* `src/commands.py` — реализация команд `ls`, `cd`, `find`,
  `tac`, `touch`, `help`;
* `tests/` — XML-файлы VFS, стартовые скрипты и `.bat`-сценарии;
* `run.bat` — запуск приложения в Windows;
* `config.toml` — конфигурационный файл приложения;
* `.gitignore` — исключения для git;
* `README.md` — описание проекта.

## Команды

Приглашение формируется из реальных данных ОС:
`username@hostname:~/путь$`, где `~` соответствует корню VFS.
Пути могут быть абсолютными (`/home/student`) и относительными
(`documents`, `../downloads`, `.`).

### ls

```text
ls [-a] [-l] [-h] [path]
```

Выводит содержимое каталога (или имя файла). Без `path`
используется текущий каталог. Записи отсортированы по имени.

* `-a` — показывать скрытые записи (имена на точку), а также
  `.` и `..`;
* `-l` — подробный формат: права, число ссылок, владелец, группа,
  размер, время изменения, имя;
* `-h` — размеры в удобном виде (`4.0K`, `1.5K`, `11K`); действует
  вместе с `-l`.

Флаги можно объединять в любом порядке и количестве:
`-la`, `-hla`, `-alh`, `-l -a -h`. Для каталогов размер равен 4096.

### cd

```text
cd [path]
```

Меняет текущий каталог. Без аргумента, а также для `~`
выполняется переход в корень VFS.

### find

```text
find [path...] [-name pattern] [-type f|d]
```

Рекурсивно выводит записи, лежащие в указанных каталогах
(по умолчанию `.`), включая сам каталог. Пути выводятся в том
виде, в котором они заданы.

* `-name pattern` — фильтр по имени с шаблонами `*`, `?`, `[...]`
  (шаблон с `*` нужно брать в кавычки);
* `-type f` — только файлы, `-type d` — только каталоги.

### tac

```text
tac file...
```

Выводит строки каждого файла в обратном порядке. Если файл
содержит байты, не являющиеся корректным UTF-8, они выводятся
в виде `\xNN`.

### touch

```text
touch [-c] file...
```

Если файл существует, обновляет время его изменения. Если файла
нет, создаёт пустой файл в уже существующем каталоге. Флаг `-c`
отключает создание новых файлов. Изменения действуют только в
памяти.

### help

```text
help
```

Выводит список команд с кратким описанием их работы.

### exit

Завершает работу эмулятора.

## Настройки

Параметры командной строки:

* `--vfs-path` — путь к XML-файлу VFS;
* `--startup-script` — путь к стартовому скрипту;
* `--config` — путь к конфигурационному файлу TOML (обязательный).

Конфигурационный файл содержит те же параметры:

```toml
vfs_path = "tests/vfs_minimal.xml"
startup_script = "tests/startup_minimal.txt"
```

Значения из командной строки имеют приоритет над значениями
из файла. При запуске выводится итоговая конфигурация:

```text
Emulator configuration:
VFS path: tests/vfs_minimal.xml
Startup script: tests/startup_minimal.txt
Config file: config.toml
```

## Формат VFS

VFS описывается XML-файлом. Содержимое файлов записывается
в Base64 (атрибут `encoding="base64"`), поэтому в файлах можно
хранить и двоичные данные. Допускается перенос длинной
Base64-строки на несколько строк. Файл без атрибута `encoding`
считается обычным текстом в UTF-8.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<vfs>
    <file name="welcome.txt" encoding="base64">TmVzdGVkIFZGUyBleGFtcGxlLgo=</file>
    <directory name="home">
        <directory name="student">
            <directory name="documents">
                <file name="report.txt" encoding="base64">VGhpcyBmaWxlIGlzIGluc2lkZSB0aHJlZSBkaXJlY3RvcnkgbGV2ZWxzLgo=</file>
                <file name="todo.txt" encoding="base64">UmV2aWV3IHRoZSBWRlMgc3RhZ2UuCg==</file>
            </directory>
            <directory name="downloads">
                <file name="data.txt" encoding="base64">RXhhbXBsZSBkb3dubG9hZGVkIGRhdGEuCg==</file>
            </directory>
        </directory>
    </directory>
</vfs>
```

Получить Base64-строку для своего текста можно так:

```bat
python -c "import base64; print(base64.b64encode(b'Hello\n').decode())"
```

Имена не должны содержать `/`, быть равными `.` или `..`
и повторяться внутри одного каталога.

## Стартовый скрипт

Перед интерактивным режимом выполняются команды из стартового
скрипта (по одной в строке). Каждая команда выводится вместе
с приглашением, имитируя диалог с пользователем. При первой
ошибке выполнение скрипта прекращается. Команда `exit` в скрипте
завершает эмулятор.

Если ввод идёт не с клавиатуры (`< файл`), введённые команды
дополнительно выводятся на экран. Конец ввода (Ctrl+D, Ctrl+Z
или конец файла) завершает интерактивный режим.

## Запуск

```bat
run.bat
python src\main.py --config config.toml
python src\main.py --config config.toml --vfs-path tests\vfs_nested.xml --startup-script tests\startup_nested.txt
```

## Тестирование

Тесты запускаются из корня репозитория. Каждый `.bat`-файл
в `tests/` запускает эмулятор с нужной VFS и стартовым скриптом.

| Сценарий | VFS | Что проверяется |
|----------|-----|-----------------|
| `test_minimal.bat` | `vfs_minimal.xml` (один файл) | `help`, `ls`, `ls -l`, `tac`, `touch` создаёт файл |
| `test_files.bat` | `vfs_files.xml` (несколько файлов, скрытый и пустой файл) | все сочетания флагов `ls` (`-a`, `-l`, `-lh`, `-hla`, `-alh`), `tac` для нескольких и пустого файлов, `touch` нескольких файлов |
| `test_nested.bat` | `vfs_nested.xml` (3+ уровня) | `cd`, `find` (`-name`, `-type`, относительные и абсолютные пути), `tac`, `touch` в других каталогах, `touch -c`, `touch` существующего файла |
| `test_binary.bat` | `vfs_binary.xml` (двоичный файл, файлы 1.5K и 11K) | размеры `ls -lh`, `tac` двоичных данных, `touch` без создания |
| `test_errors.bat` | `vfs_nested.xml`, `vfs_broken.xml`, отсутствующий файл | остановка скрипта на первой ошибке, ошибки загрузки VFS, ошибки всех команд в интерактивном режиме (`repl_errors.txt`) |

Стартовые скрипты лежат рядом: `startup_*.txt`.
`startup_errors.txt` намеренно завершается ошибкой, а
`repl_errors.txt` подаётся на вход эмулятора как ввод
пользователя и содержит по одной ошибочной команде каждого вида.

## Обработка ошибок

Все ошибки команд выводятся в формате `shell: команда: сообщение`.

```text
shell: command not found: unknown
shell: ls: invalid option -- 'z'
shell: ls: cannot access '/missing': No such file or directory
shell: ls: too many arguments
shell: cd: not a directory: welcome.txt
shell: cd: directory not found: /missing
shell: find: '/missing': No such file or directory
shell: find: unknown predicate '-bogus'
shell: find: missing argument to '-name'
shell: find: unknown argument to -type: 'x'
shell: tac: missing file operand
shell: tac: home: Is a directory
shell: tac: nofile.txt: No such file or directory
shell: touch: missing file operand
shell: touch: cannot touch '/missing/file.txt': No such file or directory
shell: touch: cannot touch 'welcome.txt/child': Not a directory
shell: help: too many arguments
```

Остальные ошибки:

* `shell: config error: ...` — не найден или некорректен TOML;
* `shell: startup script error: ...` — не удалось открыть скрипт;
* `shell: startup script execution failed` — ошибка в команде
  стартового скрипта, выполнение остановлено;
* `shell: VFS error: ...` — файл VFS не найден, XML или Base64
  некорректны.

## Пример

```text
root@vm:~$ cd home/student
root@vm:~/home/student$ find /home -name "*.txt"
/home/student/documents/report.txt
/home/student/documents/todo.txt
/home/student/downloads/data.txt
root@vm:~/home/student$ cd documents
root@vm:~/home/student/documents$ tac report.txt todo.txt
This file is inside three directory levels.
Review the VFS stage.
root@vm:~/home/student/documents$ touch notes.md
root@vm:~/home/student/documents$ ls -la
drwxr-xr-x 1 root root 4096 Oct 11 11:26 .
drwxr-xr-x 1 root root 4096 Oct 11 11:26 ..
-rw-r--r-- 1 root root    0 Oct 11 11:26 notes.md
-rw-r--r-- 1 root root   44 Oct 11 11:26 report.txt
-rw-r--r-- 1 root root   22 Oct 11 11:26 todo.txt
root@vm:~/home/student/documents$ touch -c missing.txt
root@vm:~/home/student/documents$ touch /nowhere/file.txt
shell: touch: cannot touch '/nowhere/file.txt': No such file or directory
root@vm:~/home/student/documents$ exit
```
