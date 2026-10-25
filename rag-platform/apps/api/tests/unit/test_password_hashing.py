from src.core.security import UNUSABLE_PASSWORD, hash_password, verify_password


def test_hash_is_not_the_password_and_verifies():
    hashed = hash_password("correct horse")

    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong horse", hashed)


def test_same_password_hashes_differently_each_time():
    assert hash_password("correct horse") != hash_password("correct horse")


def test_unusable_password_never_verifies():
    assert not verify_password("!", UNUSABLE_PASSWORD)
    assert not verify_password("", UNUSABLE_PASSWORD)
