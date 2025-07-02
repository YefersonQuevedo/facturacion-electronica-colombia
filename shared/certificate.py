import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from typing import NamedTuple

from .config import Config
from shared import generic

_config = Config()

class CertificateData(NamedTuple):
    private_key: object
    firmante: object
    emisor: object
    ca_raiz: object
    politica_file: object

class CertificateLoader:
    def __init__(self):
        self._sign_path = os.path.join(_config.PATH_BASE, 'certificados', _config.SIGN_NAME)
        self._sign_password = _config.SIGN_PASSWORD
        self._security = None
        self._politica_path = os.path.join(_config.PATH_BASE, 'certificados', _config.POLITICA_NAME)

    def load(self):
        print(f"[DEBUG] Ruta del certificado: {self._sign_path}")
        if not os.path.exists(self._sign_path):
            raise FileNotFoundError(f"❌ El archivo no se encontró en: {self._sign_path}")
        
        with open(self._sign_path, 'rb') as pfx_file:
            pfx_data = pfx_file.read()
            print(f"[DEBUG] Tamaño del archivo PFX: {len(pfx_data)} bytes")

        try:
            private_key, firmante, additional_certs = pkcs12.load_key_and_certificates(
                pfx_data,
                self._sign_password.encode('utf-8'),  # prueba 'latin-1' si falla
                backend=default_backend()
            )
            print("✅ Certificado cargado exitosamente.")
        except ValueError as e:
            print("❌ Error al cargar el certificado:")
            print("   - Contraseña incorrecta, o")
            print("   - Archivo PFX corrupto, o")
            print("   - El archivo no es un PKCS12 válido.")
            raise e

        if not additional_certs or len(additional_certs) < 2:
            print("⚠️ Advertencia: El certificado no contiene suficientes autoridades adicionales.")
            print(f"   - Certificados encontrados: {len(additional_certs)}")

        data = {
            'private_key': private_key,
            'firmante': firmante,
            'emisor': additional_certs[0] if additional_certs else None,
            'ca_raiz': additional_certs[1] if len(additional_certs) > 1 else None,
            'politica_file': ''  # puedes descomentar si usas la política
            # 'politica_file': generic.read_file(path=self._politica_path, mode='rb')
        }

        self._security = CertificateData(**data)

    @property
    def security(self):
        if not self._security:
            raise ValueError("Certificate data has not been loaded.")
        return self._security

certificate_loader = CertificateLoader()
