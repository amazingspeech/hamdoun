from security import api_keys


def test_hash_en_verifieer_round_trip():
    hash_hex, salt_hex = api_keys.hash_key("geheime-key-123")
    assert api_keys.verifieer_key("geheime-key-123", hash_hex, salt_hex) is True


def test_verifieer_wijst_verkeerde_key_af():
    hash_hex, salt_hex = api_keys.hash_key("geheime-key-123")
    assert api_keys.verifieer_key("andere-key", hash_hex, salt_hex) is False


def test_verifieer_faalt_niet_hard_bij_corrupte_salt():
    hash_hex, _ = api_keys.hash_key("geheime-key-123")
    assert api_keys.verifieer_key("geheime-key-123", hash_hex, "niet-hex") is False


def test_laad_keys_geeft_lege_dict_als_bestand_ontbreekt(tmp_path):
    assert api_keys.laad_keys(tmp_path / "ontbreekt.json") == {}


def test_voeg_key_toe_en_vind_key_naam(tmp_path):
    pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(pad, "klant-a", "key-voor-klant-a")
    api_keys.voeg_key_toe(pad, "klant-b", "key-voor-klant-b")

    assert api_keys.vind_key_naam(pad, "key-voor-klant-a") == "klant-a"
    assert api_keys.vind_key_naam(pad, "key-voor-klant-b") == "klant-b"
    assert api_keys.vind_key_naam(pad, "onbekende-key") is None


def test_voeg_key_toe_zet_chmod_600(tmp_path):
    pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(pad, "klant-a", "key-voor-klant-a")
    assert oct(pad.stat().st_mode)[-3:] == "600"


def test_intrekken_van_een_key_raakt_andere_keys_niet(tmp_path):
    pad = tmp_path / "api_keys.json"
    api_keys.voeg_key_toe(pad, "klant-a", "key-a")
    api_keys.voeg_key_toe(pad, "klant-b", "key-b")

    keys = api_keys.laad_keys(pad)
    del keys["klant-a"]
    import json
    pad.write_text(json.dumps(keys), encoding="utf-8")

    assert api_keys.vind_key_naam(pad, "key-a") is None
    assert api_keys.vind_key_naam(pad, "key-b") == "klant-b"
