import os
import re
import base64
import hashlib
import datetime
import threading

from shared import Config, generic
from domain.xml_models import InvoiceXml
from domain.dtos import ControlDto, InvoiceDto
from ..sign_docs.xml_signerv3 import XmlSignerV3
from ..soap.soap_invoice import SoapRequest
from ..soap.soap_test import SoapRequestTest

_config = Config()

class CreateInvoiceCase:
    def __init__(self, invoice: InvoiceDto):
        self.invoice = invoice
        self.xml = InvoiceXml()
        self.soap_invoice = SoapRequest()
        self.soap_test = SoapRequestTest(invoice.Control.TestID)

        self.xml_name = f'FV{self.invoice.ID}.xml'
        self.zip_name = f'FV{self.invoice.ID}.zip'
        self.zip_full_path = os.path.join(
            _config.PATH_BASE,
            self.invoice.Control.InvoiceAuthorization,
            'XMLFacturas',
            self.zip_name
        )

    @property
    def cufe(self):
        # ⚠️ NO tocar: misma lógica que tenías
        data = {
            "NumFac": self.invoice.ID,
            "FecFac": self.invoice.IssueDate,
            "HorFac": self.invoice.IssueTime,
            "ValFac": self.invoice.Amounts.LineExtensionAmount,
            "CodImp1": '01',
            "ValImp1": self.invoice.Amounts.TaxTotals[0].TaxAmount,  # IVA como lo tenías
            "CodImp2": '04',
            "ValImp2": '0.00',
            "CodImp3": '03',
            "ValImp3": '0.00',
            "ValTot": self.invoice.Amounts.TaxInclusiveAmount,
            "NitOFE": self.invoice.Company.CompanyID,
            "NumAdq": self.invoice.Customer.ID,
            "ClTec": self.invoice.Control.TechnicalKey,
            "TipoAmbiente": self.invoice.Control.ProfileExecutionID
        }
        return self.xml.get_cufe(data)

    def _create(self):
        # Construcción del XML (sin cambios funcionales)
        self._set_control(self.invoice.Control)
        self._set_company()
        self._set_customer()
        self._set_invoice()
        self._set_amounts()
        self._set_payment()
        self._set_lines()

        self.signer = XmlSignerV3(self.xml.get_root, self.invoice, 'FV')
        signed_invoice = self.signer.sign()
        return signed_invoice

    # ===== PRODUCCIÓN (síncrono) =====
    def send(self):
        signed_invoice = self._create()

        # Comprimir y guardar
        zip_invoice = generic.zip_document(signed_invoice, self.xml_name)
        threading.Thread(
            target=generic.write_file_from_base64,
            args=(zip_invoice, self.zip_full_path),
            daemon=True
        ).start()

        # Enviar a DIAN
        try:
            response = self.soap_invoice.send_xml(zip_invoice)
            is_valid, messages = generic.extract_errors_invoice(response.text)
        except Exception as e:
            print(f"Error al enviar la factura. XML enviado: {self.xml_name}")
            print(f"Error al enviar la factura. Respuesta XML: {e}")
            raise

        # Metadatos del ZIP (sin tocar CUFE/IVA)
        zip_bytes = base64.b64decode(zip_invoice)
        zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
        zip_size = len(zip_bytes)

        # Totales (sin tocar lógica)
        total_tax_amount = sum(float(t.TaxAmount) for t in self.invoice.Amounts.TaxTotals)

        # Estado
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        send_status = 'ACCEPTED' if is_valid == 'true' else ('REJECTED' if is_valid == 'false' else 'SENT')

        # Payload completo para tu DB (no afecta al CUFE)
        payload = {
            # Identidad / control
            "document_type": "INVOICE",
            "internal_factura": getattr(self.invoice, "InternalFactura", 0),
            "prefix": self.invoice.Control.Prefix,
            "consecutive": str(self.invoice.ID),
            "environment": int(self.invoice.Control.ProfileExecutionID),
            "authorization": self.invoice.Control.InvoiceAuthorization,
            "cufe": self.cufe,
            "qrcode_url": f'{self._qr_base()}/document/searchqr?documentkey={self.cufe}',

            # Fechas
            "issue_date": self.invoice.IssueDate,
            "issue_time": self.invoice.IssueTime,  # la de siempre; si tu DB necesita HH:MM:SS, recorta allí
            "period_start": getattr(self.xml, "PeriodStartDate", None),
            "period_end": getattr(self.xml, "PeriodEndDate", None),

            # Totales
            "subtotal": self.invoice.Amounts.LineExtensionAmount,
            "tax_exclusive": self.invoice.Amounts.TaxExclusiveAmount,
            "tax_inclusive": self.invoice.Amounts.TaxInclusiveAmount,
            "prepaid": self.invoice.Amounts.PrepaidAmount,
            "payable": self.invoice.Amounts.PayableAmount,
            "tax_total": f"{total_tax_amount:.2f}",

            # Pago
            "payment_means_id": self.invoice.Payment.PaymentID,
            "payment_code": self.invoice.Payment.PaymentCode,

            # Snapshot emisor
            "company_id": self.invoice.Company.CompanyID,
            "company_doc_type": self.invoice.Company.DocumentType,
            "company_verification_digit": self.invoice.Company.VerificationDigit,
            "company_name": self.invoice.Company.PartyName,
            "company_address_id": self.invoice.Company.Address.AddressID,
            "company_city": self.invoice.Company.Address.CityName,
            "company_state": self.invoice.Company.Address.CountrySubentity,
            "company_state_code": self.invoice.Company.Address.CountrySubentityCode,
            "company_address_line": self.invoice.Company.Address.AddressLine,

            # Snapshot adquirente
            "customer_id": self.invoice.Customer.ID,
            "customer_doc_type": self.invoice.Customer.DocumentType,
            "customer_name": self.invoice.Customer.PartyName,
            "customer_tax_level_code": self.invoice.Customer.TaxLevelCode,
            "customer_address_id": self.invoice.Customer.Address.AddressID,
            "customer_city": self.invoice.Customer.Address.CityName,
            "customer_state": self.invoice.Customer.Address.CountrySubentity,
            "customer_state_code": self.invoice.Customer.Address.CountrySubentityCode,
            "customer_address_line": self.invoice.Customer.Address.AddressLine,

            # Software / proveedor
            "software_id": self.invoice.Control.SoftwareID,
            "technical_key": self.invoice.Control.TechnicalKey,
            "software_security_code": f"{self.invoice.Control.SoftwareID}{self.invoice.Control.Pin}{self.invoice.ID}",
            "provider_id": self.invoice.Control.ProviderID,

            # Archivos
            "xml_name": self.xml_name,
            "zip_name": self.zip_name,
            "zip_path": self.zip_full_path,
            "zip_sha256": zip_sha256,
            "zip_size": zip_size,

            # Estado / DIAN
            "send_status": send_status,
            "dian_is_valid": (is_valid == 'true'),
            "dian_track_id": None,
            "dian_messages": messages,
            "last_sent_at": now,
            "validated_at": now if is_valid == 'true' else None,
            "retries": 0,

            # Firma (si decides extraerlo luego del XML firmado)
            "signature_value": None,
            "certificate_serial": None,
            "signed_at": None,

            # Auditoría
            "idempotency_key": f"{self.invoice.Control.Prefix}-{self.invoice.ID}-{self.invoice.Control.ProfileExecutionID}",
            "source_system": "python-invoice-service"
        }

        if is_valid == 'false':
            # Mantengo el raise que ya tenías
            print(f"Rechazado por DIAN. Respuesta: {response.text}")
            raise Exception(messages)

        return payload

    # ===== PRUEBAS (asíncrono) =====
    def send_test(self):
        signed_invoice = self._create()

        zip_invoice = generic.zip_document(signed_invoice, self.xml_name)
        threading.Thread(
            target=generic.write_file_from_base64,
            args=(zip_invoice, self.zip_full_path),
            daemon=True
        ).start()

        try:
            response = self.soap_test.send_xml(zip_invoice)
            # Igual que antes: dejo {status, text} para que tu WinForms siga igual
            return { "status": response.status_code, "text": response.text }
        except Exception as e:
            print(f"Error al enviar la factura. XML enviado: {self.xml_name}")
            print(f"Error al enviar la factura. Respuesta XML: {e}")
            raise

    # -------- Setters XML (sin cambios de negocio) --------
    def _set_customer(self):
        self.xml.Customer.AdditionalAccountID = self.invoice.Customer.AdditionalAccountID
        self.xml.Customer.PartyName = self.invoice.Customer.PartyName
        self.xml.Customer.CompanyID = self.invoice.Customer.ID
        self.xml.Customer.DocumentType = self.invoice.Customer.DocumentType
        self.xml.Customer.PartyIdentificationID = self.invoice.Customer.ID
        self.xml.Customer.TaxLevelCode = self.invoice.Customer.TaxLevelCode

        self.xml.Customer.AddressID = self.invoice.Customer.Address.AddressID
        self.xml.Customer.AddressCountrySubentityCode = self.invoice.Customer.Address.CountrySubentityCode
        self.xml.Customer.AddressCityName = self.invoice.Customer.Address.CityName
        self.xml.Customer.AddressCountrySubentity = self.invoice.Customer.Address.CountrySubentity
        self.xml.Customer.AddressLine = self.invoice.Customer.Address.AddressLine

        self.xml.Customer.RegistrationName = self.invoice.Customer.PartyName
        self.xml.Customer.RegistrationID = self.invoice.Customer.ID
        self.xml.Customer.RegistrationCountrySubentityCode = self.invoice.Customer.Address.CountrySubentityCode
        self.xml.Customer.RegistrationCityName = self.invoice.Customer.Address.CityName
        self.xml.Customer.RegistrationCountrySubentity = self.invoice.Customer.Address.CountrySubentity
        self.xml.Customer.RegistrationAddressLine = self.invoice.Customer.Address.AddressLine

        self.xml.Customer.LegalRegistrationName = self.invoice.Customer.PartyName
        self.xml.Customer.LegalCompanyID = self.invoice.Customer.ID
        self.xml.Customer.LegalDocumentType = self.invoice.Customer.DocumentType

    def _set_company(self):
        self.xml.Company.AdditionalAccountID = self.invoice.Company.AdditionalAccountID
        self.xml.Company.PartyName = self.invoice.Company.PartyName
        self.xml.Company.CompanyID = self.invoice.Company.CompanyID
        self.xml.Company.DocumentType = self.invoice.Company.DocumentType
        self.xml.Company.VerificationDigit = self.invoice.Company.VerificationDigit
        self.xml.Company.TaxLevelCode = self.invoice.Company.TaxLevelCode

        self.xml.Company.AddressID = self.invoice.Company.Address.AddressID
        self.xml.Company.AddressCityName = self.invoice.Company.Address.CityName
        self.xml.Company.AddressCountrySubentityCode = self.invoice.Company.Address.CountrySubentityCode
        self.xml.Company.AddressCountrySubentity = self.invoice.Company.Address.CountrySubentity
        self.xml.Company.AddressLine = self.invoice.Company.Address.AddressLine

        self.xml.Company.RegistrationName = self.invoice.Company.PartyName
        self.xml.Company.RegistrationID = self.invoice.Company.Address.AddressID
        self.xml.Company.RegistrationCityName = self.invoice.Company.Address.CityName
        self.xml.Company.RegistrationCountrySubentityCode = self.invoice.Company.Address.CountrySubentityCode
        self.xml.Company.RegistrationCountrySubentity = self.invoice.Company.Address.CountrySubentity
        self.xml.Company.RegistrationAddressLine = self.invoice.Company.Address.AddressLine

        self.xml.Company.LegalRegistrationName = self.invoice.Company.PartyName
        self.xml.Company.LegalCompanyID = self.invoice.Company.CompanyID
        self.xml.Company.LegalDocumentType = self.invoice.Company.DocumentType
        self.xml.Company.LegalVerificationDigit = self.invoice.Company.VerificationDigit

        self.xml.Company.CorporateRegistrationID = self.invoice.Control.Prefix

    def _set_lines(self):
        for index, line in enumerate(self.invoice.Lines):
            line.ID = index + 1
            self.xml.add_invoice_line(line.__dict__)

    def _set_amounts(self):
        self.xml.Amounts.LineExtensionAmount = self.invoice.Amounts.LineExtensionAmount
        self.xml.Amounts.TaxExclusiveAmount = self.invoice.Amounts.TaxExclusiveAmount
        self.xml.Amounts.TaxInclusiveAmount = self.invoice.Amounts.TaxInclusiveAmount
        self.xml.Amounts.PrepaidAmount = self.invoice.Amounts.PrepaidAmount
        self.xml.Amounts.PayableAmount = self.invoice.Amounts.PayableAmount

        for item in self.invoice.Amounts.TaxTotals:
            tax_data = {"tax_amount": item.TaxAmount, "lines": item.TaxSubtotal}
            self.xml.add_tax_total(**tax_data)

    def _set_payment(self):
        self.xml.Payment.PaymentID = self.invoice.Payment.PaymentID
        self.xml.Payment.PaymentCode = self.invoice.Payment.PaymentCode

    def _set_invoice(self):
        firt_day, last_day = generic.get_period(self.invoice.IssueDate)
        self.xml.ID = self.invoice.ID
        self.xml.IssueDate = self.invoice.IssueDate
        self.xml.IssueTime = self.invoice.IssueTime
        self.xml.LineCountNumeric = str(len(self.invoice.Lines))
        self.xml.PeriodStartDate = firt_day
        self.xml.PeriodEndDate = last_day
        self.xml.UUID = self.cufe

    def _set_control(self, control: ControlDto):
        self.xml.Control.StartDate = control.StartDate
        self.xml.Control.EndDate = control.EndDate
        self.xml.Control.InvoiceAuthorization = control.InvoiceAuthorization
        self.xml.Control.Prefix = control.Prefix
        self.xml.Control.From = control.From
        self.xml.Control.To = control.To
        self.xml.Control.ProviderID = control.ProviderID
        self.xml.Control.SoftwareID = control.SoftwareID
        self.xml.Control.SoftwareSecurityCode = f"{control.SoftwareID}{control.Pin}{self.invoice.ID}"
        qr = f'{self._qr_base()}/document/searchqr?documentkey={self.cufe}'
        self.xml.Control.QRCode = qr
        self.xml.Control.ProfileExecutionID = control.ProfileExecutionID
        self.xml.Control.VerificationDigit = self.invoice.Company.VerificationDigit

    def _qr_base(self) -> str:
        env = str(self.invoice.Control.ProfileExecutionID)
        # 1 = Producción, 2 = Habilitación
        return "https://catalogo-vpfe.dian.gov.co" if env == "1" else "https://catalogo-vpfe-hab.dian.gov.co"

