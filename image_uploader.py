import os
from google.cloud import storage

def upload_images(files):
    """Uploads a list of image files to Google Cloud Storage.

    Args:
        files: A list of file-like objects representing the images.

    Returns:
        A list of URLs for the uploaded images.
    """

    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        raise ValueError("BUCKET_NAME environment variable not set.")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    urls = []

    for file in files:
        filename = file.filename
        blob = bucket.blob(filename)
        blob.upload_from_file(file)
        urls.append(blob.public_url)

    return urls