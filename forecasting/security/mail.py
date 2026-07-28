"""E-mailmodule voor de forecasting-app: transactionele e-mails (wachtwoord-
reset, herbestel-meldingen) via SMTP. Gebruikt de stdlib smtplib/email —
geen nieuwe dependency nodig. Verzendt via het account uit serving.config
(Zoho Mail EU op smtp.zoho.eu, niet een derde-partij-API zoals Resend)."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from typing import Optional


class MailNietGeconfigureerd(Exception):
    pass


def verstuur(
    smtp_host: Optional[str],
    smtp_poort: Optional[int],
    afzender: Optional[str],
    smtp_gebruiker: Optional[str],
    smtp_wachtwoord: Optional[str],
    ontvanger: str,
    onderwerp: str,
    tekst: str,
) -> None:
    """Verstuurt één platte-tekst-e-mail. Faalt hard en vooraf (niet pas op
    een cryptische SMTP-fout) als de configuratie geheel of gedeeltelijk
    ontbreekt — mail is optioneel in serving.config, dus deze check hoort
    hier, niet daar."""
    if not all([smtp_host, smtp_poort, afzender, smtp_gebruiker, smtp_wachtwoord]):
        raise MailNietGeconfigureerd(
            "Mailinstellingen ontbreken of zijn onvolledig (MAIL_SMTP_HOST/"
            "MAIL_SMTP_POORT/MAIL_AFZENDER/MAIL_SMTP_GEBRUIKER/MAIL_SMTP_WACHTWOORD)."
        )

    bericht = MIMEText(tekst, "plain", "utf-8")
    bericht["Subject"] = onderwerp
    bericht["From"] = afzender
    bericht["To"] = ontvanger

    with smtplib.SMTP(smtp_host, smtp_poort) as server:
        server.starttls()
        server.login(smtp_gebruiker, smtp_wachtwoord)
        server.sendmail(afzender, [ontvanger], bericht.as_string())
