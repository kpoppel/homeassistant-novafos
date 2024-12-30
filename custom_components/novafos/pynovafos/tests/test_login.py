import pytest
from datetime import datetime
import random
import string

@pytest.mark.skip(reason="Login using Selenium does not work due to ReCAPTCHA.")
def test_login_using_selenium(novafos):
    novafos.authenticate_using_selenium("https://localhost")
    assert True

@pytest.mark.skip(reason="Login using OICD does not work due to ReCAPTCHA.")
def test_login_using_oicd(novafos):
    assert True

def test_login_using_access_token(mocker, novafos):
    # Too short
    access_token = "too_short"
    access_token_date_updated = datetime.now()
    assert novafos.authenticate_using_access_token(access_token, access_token_date_updated) == False

    # Okay length but out of date
    rand = random.SystemRandom()
    access_token = ''.join(rand.choices(string.ascii_letters + string.digits, k=1200))
    access_token_date_updated = datetime.now()
    assert novafos.authenticate_using_access_token(access_token, access_token_date_updated) == True

    # Okay length but out of date (Okay, since validation happens elsewhere)
    # TODO: Consider validating token age here instead of somewhere else in te code.
    access_token_date_updated = datetime(2000,1,1)
    assert novafos.authenticate_using_access_token(access_token, access_token_date_updated) == True

