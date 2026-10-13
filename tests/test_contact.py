import unittest
from unittest.mock import patch

from app import ContactRateLimited, app


class ContactApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.headers = {'Origin': 'https://www.trombonanza.org'}
        self.valid_payload = {
            'name': 'テスト 太郎',
            'email': 'taro@example.com',
            'message': 'お問い合わせ本文です。',
            'website': '',
        }

    def test_rejects_unknown_origin(self):
        response = self.client.post(
            '/api/contact',
            json=self.valid_payload,
            headers={'Origin': 'https://evil.example'},
        )
        self.assertEqual(response.status_code, 403)

    def test_rejects_invalid_fields(self):
        response = self.client.post(
            '/api/contact',
            json={**self.valid_payload, 'email': 'invalid'},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)

    @patch('app.send_contact_email')
    def test_accepts_app_engine_origin(self, send_contact_email):
        response = self.client.post(
            '/api/contact',
            json=self.valid_payload,
            headers={'Origin': 'https://trombonanza-page.uc.r.appspot.com'},
        )
        self.assertEqual(response.status_code, 200)
        send_contact_email.assert_called_once()

    @patch('app.send_contact_email')
    def test_sends_valid_contact(self, send_contact_email):
        response = self.client.post(
            '/api/contact',
            json=self.valid_payload,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        send_contact_email.assert_called_once_with('テスト 太郎', 'taro@example.com', 'お問い合わせ本文です。')

    @patch('app.send_contact_email')
    def test_honeypot_returns_success_without_email(self, send_contact_email):
        response = self.client.post(
            '/api/contact',
            json={**self.valid_payload, 'website': 'https://spam.example'},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        send_contact_email.assert_not_called()

    @patch('app.send_contact_email', side_effect=RuntimeError('failed'))
    def test_returns_gateway_error_when_delivery_fails(self, _send_contact_email):
        with self.assertLogs(level='ERROR'):
            response = self.client.post(
                '/api/contact',
                json=self.valid_payload,
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 502)

    @patch('app.send_contact_email', side_effect=ContactRateLimited())
    def test_returns_rate_limit_response(self, _send_contact_email):
        response = self.client.post(
            '/api/contact',
            json=self.valid_payload,
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 429)


if __name__ == '__main__':
    unittest.main()
