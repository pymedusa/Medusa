# coding=utf-8
#
# Copyright (C) AB Strakt
# Copyright (C) Jean-Paul Calderone
# See LICENSE for details.
#
# Modified from source:
# https://github.com/pyca/pyopenssl/blob/d52975cef3a36e18552aeb23de7c06aa73d76454/examples/certgen.py

"""Certificate generation module."""

from OpenSSL import crypto

TYPE_RSA = crypto.TYPE_RSA
TYPE_DSA = crypto.TYPE_DSA


def create_key_pair(key_type, bits):
    """
    Create a public/private key pair.

    Arguments: key_type - Key type, must be one of TYPE_RSA and TYPE_DSA
               bits     - Number of bits to use in the key
    Returns:   The public/private key pair in a PKey object
    """
    pkey = crypto.PKey()
    pkey.generate_key(key_type, bits)
    return pkey


def create_cert_request(pkey, digest='sha256', **name):
    """
    Create a certificate request.

    Arguments: pkey   - The key to associate with the request
               digest - Digestion method to use for signing, default is sha256
               **name - The name of the subject of the request, possible
                        arguments are:
                          C     - Country name
                          ST    - State or province name
                          L     - Locality name
                          O     - Organization name
                          OU    - Organizational unit name
                          CN    - Common name
                          emailAddress - E-mail address
    Returns:   The certificate request in an X509Req object
    """
    req = crypto.X509Req()
    subj = req.get_subject()

    for key, value in name.items():
        setattr(subj, key, value)

    req.set_pubkey(pkey)
    req.sign(pkey, digest)
    return req


def create_certificate(req, issuer_cert_key, serial, validity_period, digest='sha256'):
    """
    Generate a certificate given a certificate request.

    Arguments: req         - Certificate request to use
               issuer_cert - The certificate of the issuer
               issuer_key  - The private key of the issuer
               serial      - Serial number for the certificate
               not_before  - Timestamp (relative to now) when the certificate
                             starts being valid
               not_after   - Timestamp (relative to now) when the certificate
                             stops being valid
               digest      - Digest method to use for signing, default is sha256
    Returns:   The signed certificate in an X509 object
    """
    issuer_cert, issuer_key = issuer_cert_key
    not_before, not_after = validity_period
    cert = crypto.X509()
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(not_before)
    cert.gmtime_adj_notAfter(not_after)
    cert.set_issuer(issuer_cert.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(issuer_key, digest)
    return cert
