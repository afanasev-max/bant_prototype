#!/usr/bin/env python3
"""
Скрипт для генерации GIGACHAT_AUTH_KEY
"""
import base64
import sys

def generate_auth_key(client_id: str, client_secret: str) -> str:
    """Генерирует base64 строку для GIGACHAT_AUTH_KEY"""
    auth_string = f"{client_id}:{client_secret}"
    return base64.b64encode(auth_string.encode()).decode()

def main():
    if len(sys.argv) != 3:
        print("Использование: python generate_auth_key.py <CLIENT_ID> <CLIENT_SECRET>")
        print("Пример: python generate_auth_key.py my_client_id my_client_secret")
        sys.exit(1)
    
    client_id = sys.argv[1]
    client_secret = sys.argv[2]
    
    auth_key = generate_auth_key(client_id, client_secret)
    
    print(f"GIGACHAT_AUTH_KEY={auth_key}")
    print("\nДобавьте эту строку в ваш .env файл")

if __name__ == "__main__":
    main()
