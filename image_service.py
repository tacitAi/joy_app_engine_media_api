import requests

def request_leonardo_image(
    controlInitImageId: str,
    prompt: str,
    initImageId: str,
    initStrength: float = 0.1,
):
    api_key = "b099bfa2-4921-47e1-a3e3-a383d7f5db1c"
    authorization = f"Bearer {api_key}"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }

    url = "https://cloud.leonardo.ai/api/rest/v1/generations"

    payload = {
        "height": 1024,
        "modelId": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3",
        "prompt": prompt,
        "width": 1024,
        "num_images": 1,
        "ultra": True,
        "styleUUID": "debdf72a-91a4-467b-bf61-cc02bdeb69c6",
        "controlnets": [
            {
                "initImageId": controlInitImageId,
                "initImageType": "UPLOADED",
                "preprocessorId": 166,
                "strengthType": "High"
            }
        ],
        "init_image_id": initImageId,
        "init_strength": initStrength
    }

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        return {"error": "Failed to generate image", "status_code": response.status_code}

    return response.json()


