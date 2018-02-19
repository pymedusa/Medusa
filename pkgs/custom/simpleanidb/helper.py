from datetime import date
import requests


def download_file(local_filename, url):
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
    return local_filename


def date_to_date(date_str):
    if not date_str:
        return None

    return date(
        *map(int, date_str.split("-"))
    )
