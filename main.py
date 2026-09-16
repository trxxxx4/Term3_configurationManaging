import getpass
import socket
import shlex
import sys

def get_prompt():
    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"{username}@{hostname}:~$ "

def parse_input(user_input):
    try:
        return shlex.split(user_input)
    except ValueError as e:
        print(f"shell: syntax error: {e}")
        return None

def main():
    while True:
        try:
            # 1. Read
            user_input = input(get_prompt())
            
            # 2. Eval / Parse
            if not user_input.strip():
                continue
                
            tokens = parse_input(user_input)
            if tokens is None:
                continue
                
            cmd = tokens[0]
            args = tokens[1:]
            
            # 3. Print / Execute
            if cmd == "exit":
                break
            elif cmd in ("ls", "cd"):
                print(f"Executing command '{cmd}' with args: {args.split}")
            else:
                print(f"shell: command not found: {cmd}")

        except KeyboardInterrupt:
            print("\nexit")
            break

if __name__ == "__main__": #защита от запуска при импорте модуля с файла
    main()