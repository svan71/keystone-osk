from keystone_osk.accents import ACCENT_VARIANTS, accent_variants_for, has_accents


def test_map_keys_are_single_lowercase_letters():
    for key in ACCENT_VARIANTS:
        assert len(key) == 1 and key.islower()


def test_all_variant_tuples_non_empty():
    for variants in ACCENT_VARIANTS.values():
        assert len(variants) > 0


def test_no_duplicate_variants_within_tuples():
    for variants in ACCENT_VARIANTS.values():
        assert len(variants) == len(set(variants))


def test_every_variant_is_single_character():
    for variants in ACCENT_VARIANTS.values():
        for v in variants:
            assert len(v) == 1


def test_has_accents_true_for_accent_capable_lowercase():
    for letter in "aeiouncy":
        assert has_accents(letter) is True


def test_has_accents_true_for_accent_capable_uppercase():
    for letter in "AEIOUNCY":
        assert has_accents(letter) is True


def test_has_accents_false_for_non_accent_letters():
    for letter in "bdfghjklmpqrstvwxz":
        assert has_accents(letter) is False


def test_has_accents_false_for_empty_string():
    assert has_accents("") is False


def test_has_accents_false_for_multi_char():
    assert has_accents("ab") is False


def test_accent_variants_for_lowercase_a():
    assert accent_variants_for("a", False) == ("à", "á", "â", "ä", "ã", "å")


def test_accent_variants_for_uppercase_a():
    assert accent_variants_for("a", True) == ("À", "Á", "Â", "Ä", "Ã", "Å")


def test_accent_variants_for_uppercase_a_with_uppercase_input():
    assert accent_variants_for("A", True) == ("À", "Á", "Â", "Ä", "Ã", "Å")


def test_accent_variants_for_uppercase_a_with_lowercase_input():
    assert accent_variants_for("a", True) == ("À", "Á", "Â", "Ä", "Ã", "Å")


def test_accent_variants_for_non_accent_letter():
    assert accent_variants_for("b", False) == ()
    assert accent_variants_for("B", True) == ()


def test_accent_variants_handles_single_n_and_y():
    assert accent_variants_for("n", False) == ("ñ",)
    assert accent_variants_for("c", False) == ("ç",)
    assert accent_variants_for("y", False) == ("ý", "ÿ")
