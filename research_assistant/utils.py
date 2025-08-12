# -*- coding: utf-8 -*-
"""
Helper utilities and decorators.

This module provides:
    - Flashing form validation errors to the user
    - Utility for uploading files to AWS S3 storage
"""

from flask import current_app, flash
from research_assistant.extensions import get_s3_client

def upload_file_to_s3(file_storage, key_name, bucket_name=None):
    """
    Upload a file to AWS S3 and return its key name.

    Args:
        file_storage (FileStorage): File object to upload.
        key_name (str): The key (path/filename) to store in the S3 bucket.
        bucket_name (str, optional): Name of the S3 bucket.
            Defaults to AWS_S3_BUCKET_NAME in application config.

    Returns:
        str: The S3 object key (key_name).

    Behavior:
        - Uses a pre-configured S3 client from application extensions.
        - Uploads the file to the specified bucket.
    """
    s3_client = get_s3_client()

    if not bucket_name:
        bucket_name = current_app.config["AWS_S3_BUCKET_NAME"]

    s3_client.upload_fileobj(file_storage, bucket_name, key_name)
    return key_name
