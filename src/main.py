import getpass
import socket
import shlex
import argparse
import sys
import tomllib

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
            
            user_input = input(get_prompt())
            
            if not user_input.strip():
                continue
                
            tokens = parse_input(user_input)
            if tokens is None:
                continue
                
            cmd = tokens[0]
            args = tokens[1:]
            

            if cmd == "exit":
                break
            elif cmd in ("ls", "cd"):
                print(f"Executing command '{cmd}' with args: {args}")
            else:
                print(f"shell: command not found: {cmd}")

        except KeyboardInterrupt:
            print("\nexit")
            break

if __name__ == "__main__":
    main()

