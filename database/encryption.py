"""应用层加密：命盘中的出生时间、出生地等强隐私字段。

即使数据库被拖库，也无法直接读取原文。
使用 Fernet 对称加密，密钥从环境变量 XUANXUE_ENCRYPTION_KEY 读取。
"""

import base64
import os

from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(Exception):
    pass


def _get_key() -> bytes:
    key = os.environ.get("XUANXUE_ENCRYPTION_KEY")
    if not key:
        raise EncryptionError(
            "环境变量 XUANXUE_ENCRYPTION_KEY 未设置。"
            "请通过 `python -m database.encryption generate-key` 生成并设置。"
        )
    return key.encode("utf-8")


_fernet: Fernet | None = None


def _cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_key())
    return _fernet


def encrypt(plaintext: str) -> str:
    """加密敏感字段，返回字符串（便于数据库存储）。"""
    if plaintext is None:
        raise EncryptionError("不能加密 None 值")
    return _cipher().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """解密敏感字段。"""
    try:
        return _cipher().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise EncryptionError("解密失败：密文无效或密钥不匹配")


def generate_key() -> str:
    """生成并打印一个新的密钥。"""
    return Fernet.generate_key().decode("utf-8")


def normalize_key(key: str) -> str:
    """将任意字符串密钥标准化为 Fernet 可用 base64 密钥。"""
    digest = base64.urlsafe_b64encode(key.encode("utf-8")).decode("utf-8")
    return digest


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate-key":
        print(generate_key())
    else:
        print("用法: python -m database.encryption generate-key")