"""Fernet 凭据加解密工具"""

import argparse
import sys
from pathlib import Path

from cryptography.fernet import Fernet


KEY_FILE = Path(__file__).resolve().parent.parent / "config" / ".secret.key"


def generate_key() -> bytes:
    """生成新的 Fernet 密钥并保存到文件"""
    key = Fernet.generate_key()
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(key)
    print(f"密钥已保存到: {KEY_FILE}")
    return key


def _load_key() -> bytes:
    if not KEY_FILE.exists():
        raise FileNotFoundError(
            f"密钥文件不存在: {KEY_FILE}\n请先运行: python -m shared.crypto --generate-key"
        )
    return KEY_FILE.read_bytes().strip()


def encrypt_value(plaintext: str) -> str:
    """加密明文字符串，返回 base64 编码的密文"""
    f = Fernet(_load_key())
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """解密密文字符串"""
    if not ciphertext:
        return ""
    f = Fernet(_load_key())
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="凭据加解密工具")
    parser.add_argument("--generate-key", action="store_true", help="生成新密钥")
    parser.add_argument("--encrypt", type=str, help="加密一个字符串")
    parser.add_argument("--decrypt", type=str, help="解密一个字符串")
    args = parser.parse_args()

    if args.generate_key:
        generate_key()
    elif args.encrypt:
        print(encrypt_value(args.encrypt))
    elif args.decrypt:
        print(decrypt_value(args.decrypt))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
