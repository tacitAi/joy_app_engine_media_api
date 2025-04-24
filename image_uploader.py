import os
from google.cloud import storage
import requests
import json
import tempfile

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

def upload_to_leonardo(image_url: str):
    api_key = "b099bfa2-4921-47e1-a3e3-a383d7f5db1c"
    authorization = f"Bearer {api_key}"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }

    # Get a presigned URL for uploading an image
    url = "https://cloud.leonardo.ai/api/rest/v1/init-image"

    # Retrieve the image from the provided URL
    image_response = requests.get(image_url, stream=True)
    if image_response.status_code != 200:
        return {"error": "Failed to retrieve image from URL", "status_code": image_response.status_code}

    # Detect the file extension
    content_type = image_response.headers.get('Content-Type')
    extension = content_type.split('/')[-1] if content_type else 'jpg'

    payload = {"extension": extension}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return {"error": "Failed to get presigned URL", "status_code": response.status_code}

    fields = json.loads(response.json()['uploadInitImage']['fields'])
    upload_url = response.json()['uploadInitImage']['url']
    image_id = response.json()['uploadInitImage']['id']

    # Upload image via presigned URL
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_image:
        for chunk in image_response.iter_content(chunk_size=8192):
            temp_image.write(chunk)
        temp_image_path = temp_image.name

    with open(temp_image_path, 'rb') as image_file:
        files = {'file': image_file}
        upload_response = requests.post(upload_url, data=fields, files=files)

    os.unlink(temp_image_path)  # Clean up temporary file

    if upload_response.status_code != 204:
        return {"error": "Failed to upload image", "status_code": upload_response.status_code}

    return {"image_id": image_id}
