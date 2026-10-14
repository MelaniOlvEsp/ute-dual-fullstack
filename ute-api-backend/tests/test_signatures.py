import unittest
from io import BytesIO

import fitz
from PIL import Image
from app.application.errors import ApplicationError
from app.infrastructure.documents.signatures import validate_signature, sign_pdf


class SignatureTests(unittest.TestCase):
    def test_signature_validation_rejects_false_content(self):
        with self.assertRaises(ApplicationError):
            validate_signature(b'<svg></svg>', 'image/png')
        with self.assertRaises(ApplicationError):
            validate_signature(b'x' * (1024 * 1024 + 1), 'image/png')

    def test_signature_appears_on_separate_pdf_page(self):
        image = Image.new('RGB', (250, 90), color='white')
        image_bytes = BytesIO()
        image.save(image_bytes, format='PNG')
        with fitz.open() as original:
            original.new_page()
            original_bytes = original.tobytes()
        signed = sign_pdf(original_bytes, image_bytes.getvalue(), 'Tutor Prueba')
        with fitz.open(stream=signed, filetype='pdf') as result:
            self.assertEqual(result.page_count, 2)
            text = result[-1].get_text()
            self.assertIn('Tutor', text)
            self.assertIn('Revisado', text)
