"""PDF 密碼解除：以 pikepdf 開啟加密 PDF 並輸出無密碼版本。

此模組僅能處理使用者「有權處理」的檔案：
  - 純 owner 密碼（僅限制列印/複製/編輯）→ 空密碼即可開啟並移除限制
  - user 密碼（開啟即需密碼）→ 必須提供正確密碼

這不是破解：有開啟密碼的檔案一定要正確密碼才能解。
"""

import pikepdf


class PasswordRequired(Exception):
    """檔案需要開啟密碼，但呼叫端未提供（或提供空密碼）。"""


class WrongPassword(Exception):
    """提供的密碼不正確。"""


def is_encrypted(input_path: str) -> bool:
    """偵測 PDF 是否加密。

    若檔案有 user 密碼，無密碼開啟會丟出 PasswordError，
    此時視為加密（需密碼）。
    """
    try:
        with pikepdf.open(input_path) as pdf:
            return pdf.is_encrypted
    except pikepdf.PasswordError:
        return True


def decrypt_pdf(input_path: str, output_path: str, password: str = "") -> None:
    """以 password 開啟 input_path，輸出不含加密的 output_path。

    save() 不指定 encryption 參數即代表輸出無密碼版本。

    Raises:
        PasswordRequired: password 為空但檔案需要密碼。
        WrongPassword: 提供的非空密碼不正確。
    """
    try:
        with pikepdf.open(input_path, password=password) as pdf:
            pdf.save(output_path)
    except pikepdf.PasswordError as exc:
        if password == "":
            raise PasswordRequired() from exc
        raise WrongPassword() from exc
