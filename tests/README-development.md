# Running tests (development)
If Home Assistant is installed as stand-alone using pip install and a venv:

```
source /srv/homeassistant/bin/activate

pip install -r requirements.test.txt

cd ~/.homeassistant/custom_componts/homeassistant-novafos
pre-commit install
```

## Run pre-commits:

```
pre-commit run --all-files
pre-commit run --show-diff-on-failure
```
or individually

```
ruff check homeassistant/core.py
pylint homeassistant/core.py
```

## Run tests
```
cd ~/.homeassistant
pytest
```
## Commit code
```
git commit -a --no-verify
```


# pytest tips

```
async def test_update_data_success(mocker, hass):  # mocker is injected by pytest-mock
    mock_get = mocker.patch("custom_components.your_integration.requests.get")
    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = b'{"key1": "value1", "key2": 123}'
    mock_get.return_value = mock_response
    data = await async_update_data(hass)
    assert data["key1"] == "value1"
    assert data["key2"] == 123
    mock_get.assert_called_once()

async def test_update_data_error(mocker, hass):
    mock_get = mocker.patch("custom_components.your_integration.requests.get")
    mock_get.side_effect = requests.exceptions.RequestException("API Error")
    with pytest.raises(requests.exceptions.RequestException):
        await async_update_data(hass)
```

## Skip a test:
```
import pytest

@pytest.mark.skip(reason="Need some data to test what is necessary here.")
```

## Mocking datetime

```
from unittest import mock

def test.---()
    with mock.patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 11, 0, 0) 
        ... more test code
```