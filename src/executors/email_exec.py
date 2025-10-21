from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Dict


@dataclass
class EmailConfig:
    host: str
    port: int
    user: str
    password: str
    from_addr: str
    use_tls: bool = True


class EmailExecutor:
    def __init__(self, cfg: EmailConfig) -> None:
        self.cfg = cfg

    def send(self, to: str, subject: str, body: str) -> Dict[str, str]:
        if not all([self.cfg.host, self.cfg.user, self.cfg.password, self.cfg.from_addr]):
            raise ValueError("SMTP not configured: host/user/password/from required")
        msg = EmailMessage()
        msg["From"] = self.cfg.from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if self.cfg.use_tls:
            with smtplib.SMTP(self.cfg.host, self.cfg.port) as s:
                s.starttls()
                s.login(self.cfg.user, self.cfg.password)
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(self.cfg.host, self.cfg.port) as s:
                s.login(self.cfg.user, self.cfg.password)
                s.send_message(msg)
        return {"status": "sent", "to": to, "subject": subject}
