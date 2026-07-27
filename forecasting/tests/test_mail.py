import email

import pytest

from security import mail


class _NepSMTP:
    aangemaakt = []

    def __init__(self, host, poort):
        self.host = host
        self.poort = poort
        self.tls_aangeroepen = False
        self.login_args = None
        self.sendmail_args = None
        type(self).aangemaakt.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.tls_aangeroepen = True

    def login(self, gebruiker, wachtwoord):
        self.login_args = (gebruiker, wachtwoord)

    def sendmail(self, afzender, ontvangers, bericht):
        self.sendmail_args = (afzender, ontvangers, bericht)


def test_verstuur_gebruikt_smtp_met_juiste_instellingen(monkeypatch):
    _NepSMTP.aangemaakt = []
    monkeypatch.setattr(mail.smtplib, "SMTP", _NepSMTP)

    mail.verstuur(
        smtp_host="smtp.zoho.eu", smtp_poort=587, afzender="info@tessar.nl",
        smtp_gebruiker="info@tessar.nl", smtp_wachtwoord="geheim",
        ontvanger="klant@voorbeeld.nl", onderwerp="Testonderwerp", tekst="Testtekst",
    )

    server = _NepSMTP.aangemaakt[0]
    assert server.host == "smtp.zoho.eu"
    assert server.poort == 587
    assert server.tls_aangeroepen is True
    assert server.login_args == ("info@tessar.nl", "geheim")
    afzender, ontvangers, bericht = server.sendmail_args
    assert afzender == "info@tessar.nl"
    assert ontvangers == ["klant@voorbeeld.nl"]
    geparsed = email.message_from_string(bericht)
    assert geparsed["Subject"] == "Testonderwerp"
    assert geparsed.get_payload(decode=True).decode("utf-8") == "Testtekst"


def test_verstuur_zonder_configuratie_faalt_hard():
    with pytest.raises(mail.MailNietGeconfigureerd):
        mail.verstuur(
            smtp_host=None, smtp_poort=None, afzender=None,
            smtp_gebruiker=None, smtp_wachtwoord=None,
            ontvanger="klant@voorbeeld.nl", onderwerp="Testonderwerp", tekst="Testtekst",
        )


def test_verstuur_faalt_hard_bij_gedeeltelijke_configuratie():
    """Half ingevulde mailconfig (bv. host wel, wachtwoord niet) mag nooit
    een verzendpoging doen die alsnog faalt op een cryptische SMTP-fout —
    liever een duidelijke eigen foutmelding vooraf."""
    with pytest.raises(mail.MailNietGeconfigureerd):
        mail.verstuur(
            smtp_host="smtp.zoho.eu", smtp_poort=587, afzender="info@tessar.nl",
            smtp_gebruiker="info@tessar.nl", smtp_wachtwoord=None,
            ontvanger="klant@voorbeeld.nl", onderwerp="Testonderwerp", tekst="Testtekst",
        )
