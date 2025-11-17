import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def generate_vapid_keypair():
    # Generate private key using SECP256R1
    private_key = ec.generate_private_key(ec.SECP256R1())

    # Get the public key
    public_key = private_key.public_key()

    # Export public key in uncompressed point format
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    # Export private key as raw integer bytes
    private_value = private_key.private_numbers().private_value
    private_bytes = private_value.to_bytes(32, "big")

    # Convert to base64url
    public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("utf-8")
    private_b64 = base64.urlsafe_b64encode(private_bytes).rstrip(b"=").decode("utf-8")

    return public_b64, private_b64
