from google.cloud import secretmanager

def access_secret(project_id, secret_id, version_id="latest"):
    """
    Access the secret with the given name and version from Secret Manager.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    
    return response.payload.data.decode("UTF-8")