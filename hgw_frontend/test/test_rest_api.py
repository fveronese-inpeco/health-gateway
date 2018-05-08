# Copyright (c) 2017-2018 CRS4
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
# AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import json
import logging
import os
import sys

from Cryptodome.PublicKey import RSA
from django.test import TestCase, client
from mock import patch

from hgw_common.cipher import Cipher
from hgw_common.models import Profile
from hgw_common.utils.test import get_free_port, start_mock_server, MockKafkaConsumer, MockMessage
from hgw_frontend import ERRORS_MESSAGE
from hgw_frontend.models import FlowRequest, ConfirmationCode, ConsentConfirmation, Destination, RESTClient
from . import WRONG_CONFIRM_ID, CORRECT_CONFIRM_ID, CORRECT_CONFIRM_ID2, \
    TEST_PERSON1_ID
from .utils import MockConsentManagerRequestHandler, MockBackendRequestHandler

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

CONSENT_MANAGER_PORT = get_free_port()
CONSENT_MANAGER_URI = 'http://localhost:{}'.format(CONSENT_MANAGER_PORT)

HGW_BACKEND_PORT = get_free_port()
HGW_BACKEND_URI = 'http://localhost:{}'.format(HGW_BACKEND_PORT)

DEST_PUBLIC_KEY = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAp4TF/ETwYKG+eAYZz3wo\n8IYqrPIlQyz1/xljqDD162ZAYJLCYeCfs9yczcazC8keWzGd5/tn4TF6II0oINKh\nkCYLqTIVkVGC7/tgH5UEe/XG1trRZfMqwl1hEvZV+/zanV0cl7IjTR9ajb1TwwQY\nMOjcaaBZj+xfD884pwogWkcSGTEODGfoVACHjEXHs+oVriHqs4iggiiMYbO7TBjg\nBe9p7ZDHSVBbXtQ3XuGKnxs9MTLIh5L9jxSRb9CgAtv8ubhzs2vpnHrRVkRoddrk\n8YHKRryYcVDHVLAGc4srceXU7zrwAMbjS7msh/LK88ZDUWfIZKZvbV0L+/topvzd\nXQIDAQAB\n-----END PUBLIC KEY-----'


class TestHGWFrontendAPI(TestCase):
    fixtures = ['test_data.json']

    @classmethod
    def setUpClass(cls):
        super(TestHGWFrontendAPI, cls).setUpClass()
        logger = logging.getLogger('hgw_frontend')
        logger.setLevel(logging.ERROR)
        start_mock_server('certs', MockConsentManagerRequestHandler, CONSENT_MANAGER_PORT)
        start_mock_server('certs', MockBackendRequestHandler, HGW_BACKEND_PORT)

    def setUp(self):
        self.client = client.Client()
        payload = '[{"clinical_domain": "Laboratory", ' \
                  '"filters": [{"excludes": "HDL", "includes": "immunochemistry"}]}, ' \
                  '{"clinical_domain": "Radiology", ' \
                  '"filters": [{"excludes": "Radiology", "includes": "Tomography"}]}, ' \
                  '{"clinical_domain": "Emergency", ' \
                  '"filters": [{"excludes": "", "includes": ""}]}, ' \
                  '{"clinical_domain": "Prescription", ' \
                  '"filters": [{"excludes": "", "includes": ""}]}]'

        self.profile = {
            'code': 'PROF002',
            'version': 'hgw.document.profile.v0',
            'payload': payload

        }

        self.flow_request_data = {
            'flow_id': '11111',
            'profile': self.profile,
            "start_validity": "2017-10-23T10:00:00",
            "expire_validity": "2018-10-23T10:00:00"
        }
        self.flow_request_json_data = json.dumps(self.flow_request_data)
        self.encypter = Cipher(public_key=RSA.importKey(DEST_PUBLIC_KEY))

    def set_mock_kafka_consumer(self, mock_kc_klass):
        mock_kc_klass.FIRST = 3
        mock_kc_klass.END = 33
        message = self.encypter.encrypt(1000000*'a')
        mock_kc_klass.MESSAGES = {i: MockMessage(key="09876".encode('utf-8'), offset=i,
                                                 topic='vnTuqCY3muHipTSan6Xdctj2Y0vUOVkj'.encode('utf-8'),
                                                 value=message) for i in range(mock_kc_klass.FIRST, mock_kc_klass.END)}

    def _create_flow_request_data(self):
        payload = '[{"clinical_domain": "Laboratory", ' \
                  '"filters": [{"excludes": "HDL", "includes": "immunochemistry"}]}, ' \
                  '{"clinical_domain": "Radiology", ' \
                  '"filters": [{"excludes": "Radiology", "includes": "Tomography"}]}, ' \
                  '{"clinical_domain": "Emergency", ' \
                  '"filters": [{"excludes": "", "includes": ""}]}, ' \
                  '{"clinical_domain": "Prescription", ' \
                  '"filters": [{"excludes": "", "includes": ""}]}]'

        self.profile = {
            'code': 'PROF002',
            'version': 'hgw.document.profile.v0',
            'payload': payload

        }

        self.flow_request_data = {
            'flow_id': '11111',
            'profile': self.profile,
            "start_validity": "2017-10-23T10:00:00",
            "expire_validity": "2018-10-23T10:00:00"
        }
        self.flow_request_json_data = json.dumps(self.flow_request_data)

    @staticmethod
    def _get_client_data(client_index=0):
        app = RESTClient.objects.all()[client_index]
        return app.client_id, app.client_secret

    def _add_flow_request(self, client_index=0):
        headers = self._get_oauth_header(client_index)
        return self.client.post('/v1/flow_requests/', data=self.flow_request_json_data,
                                content_type='application/json', **headers)

    def _get_oauth_header(self, client_index=0):
        c_id, c_secret = self._get_client_data(client_index)
        params = {
            'grant_type': 'client_credentials',
            'client_id': c_id,
            'client_secret': c_secret
        }
        res = self.client.post('/oauth2/token/', data=params)
        access_token = res.json()['access_token']
        return {"Authorization": "Bearer {}".format(access_token)}

    def test_init_fixtures(self):
        self.assertEquals(RESTClient.objects.all().count(), 3)
        self.assertEquals(Destination.objects.all().count(), 2)
        self.assertEquals(FlowRequest.objects.all().count(), 2)

    def test_oauth_flow_request_not_authorized(self):
        for m in ('post', 'get'):
            met = getattr(self.client, m)
            res = met('/v1/flow_requests/', content_type='application/json')
            self.assertEquals(res.status_code, 401)

        for m in ('put', 'get', 'delete'):
            met = getattr(self.client, m)
            res = met('/v1/flow_requests/1/')
            self.assertEquals(res.status_code, 401)

    def test_get_all_flow_requests_for_a_destination(self):
        """
        Tests get all flow requests for a destination. It returns only the ones belonging to the destination
        """
        headers = self._get_oauth_header()
        res = self.client.get('/v1/flow_requests/', **headers)
        self.assertEquals(res.status_code, 200)
        self.assertEquals(len(res.json()), 1)

    def test_get_all_flow_requests_as_super_client(self):
        """
        Tests get all flow requests from a client with super role. It returns all the flow requests
        """
        headers = self._get_oauth_header(client_index=2)
        res = self.client.get('/v1/flow_requests/', **headers)
        self.assertEquals(res.status_code, 200)
        self.assertEquals(len(res.json()), 2)

    def test_get_one_flow_requests_as_super_client(self):
        """
        Tests get all flow requests from from a client with super role. It returns all the flow requests
        """
        headers = self._get_oauth_header(client_index=2)
        res = self.client.get('/v1/flow_requests/54321/', **headers)
        self.assertEquals(res.status_code, 200)
        expected = {'flow_id': '12345',
                    'process_id': '54321',
                    'status': 'PE',
                    'profile': {
                        'code': 'PROF002',
                        'version': 'hgw.document.profile.v0',
                        'payload': '[{"clinical_domain": "Laboratory", "filters": [{"excludes": "HDL", "includes": "immunochemistry"}]}, {"clinical_domain": "Radiology", "filters": [{"excludes": "Radiology", "includes": "Tomography"}]}, {"clinical_domain": "Emergency", "filters": [{"excludes": "", "includes": ""}]}, {"clinical_domain": "Prescription", "filters": [{"excludes": "", "includes": ""}]}]'
                    },
                    'start_validity': '2017-10-23T10:00:00Z',
                    'expire_validity': '2018-10-23T10:00:00Z'
                    }
        self.assertDictEqual(res.json(), expected)

    def test_get_one_flow_request_for_a_destination(self):
        """
        Tests get of only one flow request. The flow request belongs to the destination
        """
        headers = self._get_oauth_header()
        res = self.client.get('/v1/flow_requests/54321/', **headers)
        self.assertEquals(res.status_code, 200)
        expected = {'flow_id': '12345',
                    'process_id': '54321',
                    'status': 'PE',
                    'profile': {
                        'code': 'PROF002',
                        'version': 'hgw.document.profile.v0',
                        'payload': '[{"clinical_domain": "Laboratory", "filters": [{"excludes": "HDL", "includes": "immunochemistry"}]}, {"clinical_domain": "Radiology", "filters": [{"excludes": "Radiology", "includes": "Tomography"}]}, {"clinical_domain": "Emergency", "filters": [{"excludes": "", "includes": ""}]}, {"clinical_domain": "Prescription", "filters": [{"excludes": "", "includes": ""}]}]'
                    },
                    'start_validity': '2017-10-23T10:00:00Z',
                    'expire_validity': '2018-10-23T10:00:00Z'
                    }
        self.assertDictEqual(res.json(), expected)

    def test_not_owned_flow_request(self):
        """
        Tests that when getting a flow request from the destination that doesn't own it, it returns an error
        """
        headers = self._get_oauth_header()
        res = self.client.get('/v1/flow_requests/09876/', **headers)
        self.assertEquals(res.status_code, 404)
        expected = {'detail': 'Not found.'}
        self.assertDictEqual(res.json(), expected)

    def test_add_flow_requests(self):
        """
        Tests adding a flow request. It tests that the request is added but its status is set to PENDING
        """
        res = self._add_flow_request()
        self.assertEquals(res.status_code, 201)

        fr = res.json()
        destination = Destination.objects.get(name='Destination 1')
        self.assertEquals(fr['flow_id'], self.flow_request_data['flow_id'])
        self.assertEquals(fr['status'], 'PE')
        self.assertDictEqual(fr['profile'], self.flow_request_data['profile'])
        self.assertEquals(FlowRequest.objects.all().count(), 3)
        self.assertEquals(ConfirmationCode.objects.all().count(), 1)
        self.assertEquals(FlowRequest.objects.get(flow_id=fr['flow_id']).destination, destination)

    def test_add_flow_requests_forbidden(self):
        """
        Tests adding a flow request. It tests that the request is added but its status is set to PENDING
        """
        res = self._add_flow_request(client_index=2)
        self.assertEquals(res.status_code, 403)

    def test_add_duplicated_profile_requests(self):
        self._add_flow_request()
        self.profile = {
            'code': 'PROF002',
            'version': 'hgw.document.profile.v0',
            'payload': "different_payload"
        }

        self.flow_request_data = {
            'flow_id': '11111',
            'profile': self.profile,
            "start_validity": "2017-10-23T10:00:00",
            "expire_validity": "2018-10-23T10:00:00"
        }
        self.flow_request_json_data = json.dumps(self.flow_request_data)

        res = self._add_flow_request()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), ERRORS_MESSAGE['INVALID_DATA'])

    def test_add_flow_requests_no_validity_range_provided(self):
        data = self.flow_request_data.copy()
        del data['start_validity']
        del data['expire_validity']
        headers = self._get_oauth_header()

        res = self.client.post('/v1/flow_requests/', data=json.dumps(data),
                               content_type='application/json', **headers)

        self.assertEquals(res.status_code, 201)

    def test_add_flow_request_only_one_validity_date_provided(self):
        data = self.flow_request_data.copy()
        headers = self._get_oauth_header()
        del data['start_validity']
        res = self.client.post('/v1/flow_requests/', data=json.dumps(data),
                               content_type='application/json', **headers)

        self.assertEquals(res.status_code, 400)
        data = self.flow_request_data.copy()
        del data['expire_validity']
        res = self.client.post('/v1/flow_requests/', data=json.dumps(data),
                               content_type='application/json', **headers)
        self.assertEquals(res.status_code, 400)

    def test_add_flow_requests_wrong_content_type(self):
        """
        Tests error when adding a flow request with the wrong content type (i.e., != from application/json)
        """
        headers = self._get_oauth_header()
        res = self.client.post('/v1/flow_requests/', data=self.flow_request_data, **headers)
        self.assertEquals(res.status_code, 415)

    def test_add_flow_requests_forcing_status(self):
        """
        Tests that if the requester, adding a flow request, tries to force the status to ACTIVE,
        the status is still set to PENDING
        """
        headers = self._get_oauth_header()
        # data = self.flow_request_data
        self.flow_request_data.update({'process_id': '22222', 'status': FlowRequest.ACTIVE})
        json_data = json.dumps(self.flow_request_data)
        res = self.client.post('/v1/flow_requests/', data=json_data, content_type='application/json', **headers)
        self.assertEquals(res.status_code, 201)
        fr = res.json()
        self.assertEquals(fr['flow_id'], self.flow_request_data['flow_id'])
        self.assertNotEquals(fr['process_id'], self.flow_request_data['process_id'])
        self.assertEquals(fr['status'], 'PE')
        self.assertDictEqual(fr['profile'], self.flow_request_data['profile'])
        self.assertEquals(FlowRequest.objects.all().count(), 3)

    @patch('hgw_frontend.views.flow_requests.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    @patch('hgw_frontend.views.flow_requests.HGW_BACKEND_URI', HGW_BACKEND_URI)
    def test_confirm_duplicated_consent(self):
        """
        Test that if a Consent is already present the Flow Request is not added
        """
        self._add_flow_request()
        res = self._add_flow_request()
        confirm_id = res.json()['confirm_id']
        callback_url = 'http://127.0.0.1/'

        # Then confirm the request. This will cause a redirect to consent manager
        self.client.login(username='mouse', password='duck')
        res = self.client.get('/v1/flow_requests/confirm/?confirm_id={}&callback_url={}&action=add'.format(
            confirm_id, callback_url))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode('utf-8'), 'All available consents already inserted')

    def test_confirm_redirect(self):
        """
        Tests that the confirm url redirect to saml authentication
        """
        res = self.client.get('/v1/flow_requests/confirm/')
        self.assertRedirects(res, '/saml2/login/?next=/v1/flow_requests/confirm/', fetch_redirect_response=False)

    def test_confirm_wrong_method(self):
        """
        Tests wrong method (i.e., != GET) when confirming
        """
        self.client.login(username='duck', password='duck')
        for m in ('post', 'put', 'head', 'options', 'delete', 'trace'):
            met = getattr(self.client, m)
            res = met('/v1/flow_requests/confirm/')
            self.assertEquals(res.status_code, 405)

    def test_confirm_invalid_action(self):
        headers = self._get_oauth_header()

        # using delete but it doesn't matter if it's delete or add
        res = self.client.delete('/v1/flow_requests/54321/', **headers)
        confirm_id = res.json()['confirm_id']
        callback_url = 'http://127.0.0.1/'

        self.client.login(username='duck', password='duck')
        res = self.client.get('/v1/flow_requests/confirm/?confirm_id={}&callback_url={}&action=NOT_VALID'.format(
            confirm_id, callback_url))

        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['UNKNOWN_ACTION'])

    def test_confirm_missing_parameters(self):
        """
        Test errors when confirming a flow requests and not sending the correct parameters
        """
        headers = self._get_oauth_header()

        # using delete but it doesn't matter if it's delete or add
        res = self.client.delete('/v1/flow_requests/54321/', **headers)

        confirm_id = res.json()['confirm_id']
        callback_url = 'http://127.0.0.1/'

        self.client.login(username='duck', password='duck')
        res = self.client.get('/v1/flow_requests/confirm/')
        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['MISSING_PARAM'])

        res = self.client.get(
            '/v1/flow_requests/confirm/?confirm_id={}&callback_url={}'.format(confirm_id, callback_url))
        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['MISSING_PARAM'])

        res = self.client.get('/v1/flow_requests/confirm/?confirm_id={}&action=delete'.format(confirm_id))
        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['MISSING_PARAM'])

        res = self.client.get('/v1/flow_requests/confirm/?callback_url={}&action=delete'.format(confirm_id))
        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['MISSING_PARAM'])

    def test_confirm_invalid_confirmation_code(self):
        """
        Test error when sending an invalid confirmation code to confirm url
        """
        headers = self._get_oauth_header()

        # using delete but it doesn't matter if it's delete or add
        self.client.delete('/v1/flow_requests/54321/', **headers)
        callback_url = 'http://127.0.0.1/'
        self.client.login(username='duck', password='duck')
        res = self.client.get('/v1/flow_requests/confirm/?confirm_id=invalid&callback_url={}&action=delete'.format(
            callback_url,
        ))
        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['INVALID_CONFIRMATION_CODE'])

    def test_confirm_add_wrong_flow_request_state(self):
        """
        Test errors when confirming a flow request which is not in PENDING status
        """
        # create fake flow request with active status
        profile = Profile.objects.get(pk=1)
        destination = Destination.objects.get(pk=1)
        data = {
            'flow_id': '112233',
            'process_id': '332211',
            'status': FlowRequest.ACTIVE,
            'profile': profile,
            'destination': destination,
            "start_validity": "2017-10-23T10:00:00",
            "expire_validity": "2018-10-23T10:00:00"
        }
        fr = FlowRequest.objects.create(**data)
        fr.save()
        cc = ConfirmationCode.objects.create(flow_request=fr)
        cc.save()

        callback_url = 'http://127.0.0.1/'
        self.client.login(username='duck', password='duck')
        for status in [s[0] for s in FlowRequest.STATUS_CHOICES if s[0] != FlowRequest.PENDING]:
            fr.status = status
            fr.save()
            res = self.client.get('/v1/flow_requests/confirm/?confirm_id={}&callback_url={}&action=add'.format(
                cc.code,
                callback_url
            ))
            self.assertEquals(res.status_code, 400)
            self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['INVALID_FR_STATUS'])

    def test_confirm_delete_wrong_flow_request_state(self):
        # create fake flow request with active status
        profile = Profile.objects.get(pk=1)
        destination = Destination.objects.get(pk=1)

        data = {
            'flow_id': '112233',
            'process_id': '332211',
            'status': FlowRequest.ACTIVE,
            'profile': profile,
            'destination': destination,
            "start_validity": "2017-10-23T10:00:00",
            "expire_validity": "2018-10-23T10:00:00"
        }
        fr = FlowRequest.objects.create(**data)
        fr.save()
        cc = ConfirmationCode.objects.create(flow_request=fr)
        cc.save()

        callback_url = 'http://127.0.0.1/'
        self.client.login(username='duck', password='duck')
        for status in [s[0] for s in FlowRequest.STATUS_CHOICES if s[0] != FlowRequest.DELETE_REQUESTED]:
            fr.status = status
            fr.save()
            res = self.client.get('/v1/flow_requests/confirm/?confirm_id={}&callback_url={}&action=delete'.format(
                cc.code,
                callback_url
            ))
            self.assertEquals(res.status_code, 400)
            self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['INVALID_FR_STATUS'])

    @patch('hgw_frontend.views.flow_requests.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    @patch('hgw_frontend.views.flow_requests.KafkaProducer')
    def test_confirm_missing_person_id(self, mocked_kafka_producer):
        """
        Tests that if the person logged does not have a correct ID (i.e., fiscalNumber), the confirmation fails
        :return:
        """
        self.client.login(username='admin', password='admin')
        res = self.client.get('/v1/flow_requests/confirm/?consent_confirm_id={}'.format(CORRECT_CONFIRM_ID))
        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['MISSING_PERSON_ID'])

    @patch('hgw_frontend.views.flow_requests.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    @patch('hgw_frontend.views.flow_requests.HGW_BACKEND_URI', HGW_BACKEND_URI)
    def test_confirm_add_flow_request_redirect_to_consent_manager(self):
        """
        Tests that confirmation of flow request redirect to consent manager
        """
        # First perform an add request that creates the flow request with status 'PENDING'
        res = self._add_flow_request()
        confirm_id = res.json()['confirm_id']
        callback_url = 'http://127.0.0.1/'
        previous_consent_count = ConsentConfirmation.objects.count()

        # Then confirm the request. This will cause a redirect to consent manager
        self.client.login(username='duck', password='duck')
        res = self.client.get('/v1/flow_requests/confirm/?confirm_id={}&callback_url={}&action=add'.format(
            confirm_id, callback_url))
        self.assertEquals(res.status_code, 302)
        self.assertEquals(ConsentConfirmation.objects.count(), previous_consent_count + 1)
        consent_confirm_id = ConsentConfirmation.objects.last().confirmation_id
        consent_callback_url = 'http://testserver/v1/flow_requests/consents_confirmed/'
        self.assertRedirects(res, '{}/v1/consents/confirm/?confirm_id={}&callback_url={}'.
                             format(CONSENT_MANAGER_URI, consent_confirm_id, consent_callback_url),
                             fetch_redirect_response=False)

    @patch('hgw_frontend.views.flow_requests.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    @patch('hgw_frontend.views.flow_requests.KafkaProducer')
    def test_confirm_add_flow_request_confirmed_consent(self, mocked_kafka_producer):
        """
        Tests the correct confirmation process. It checks that the FlowRequest is set to ACTIVE and that the Kafka
        message is sent
        """
        self.client.login(username='duck', password='duck')
        # Gets the confirmation code installed with the test data
        c = ConsentConfirmation.objects.get(confirmation_id=CORRECT_CONFIRM_ID)
        res = self.client.get(
            '/v1/flow_requests/consents_confirmed/?success=true&consent_confirm_id={}'.format(CORRECT_CONFIRM_ID))

        redirect_url = '{}?process_id={}&success=true'.format(c.destination_endpoint_callback_url,
                                                              c.flow_request.process_id)
        self.assertRedirects(res, redirect_url, fetch_redirect_response=False)
        fr = c.flow_request
        self.assertEquals(fr.status, FlowRequest.ACTIVE)

        destination = c.flow_request.destination
        kafka_data = {
            'channel_id': c.consent_id,
            'source_id': 'iWWjKVje7Ss3M45oTNUpRV59ovVpl3xT',
            'destination': {
                'destination_id': destination.destination_id,
                'kafka_public_key': destination.kafka_public_key
            },
            'profile': self.profile,
            'person_id': TEST_PERSON1_ID
        }
        self.assertEquals(mocked_kafka_producer().send.call_args_list[0][0][0], 'control')
        self.assertDictEqual(json.loads(mocked_kafka_producer().send.call_args_list[0][0][1].decode()), kafka_data)

    @patch('hgw_frontend.views.flow_requests.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    @patch('hgw_frontend.views.flow_requests.KafkaProducer')
    def test_confirm_add_flow_request_wrong_consent_status(self, mocked_kafka_producer):
        """
        Tests the behavior when a user try to call the /flow_requests/confirm view with a consent_confirm_id of a
        consent not confirmed. It uses flow_request with 'no_consent' and consent with id 'not_confirmed' (status PE)
        (check test data)
        :return:
        """
        self.client.login(username='duck', password='duck')
        res = self.client.get(
            '/v1/flow_requests/consents_confirmed/?success=true&consent_confirm_id={}'.format(WRONG_CONFIRM_ID))
        self.assertEquals(res.status_code, 302)
        c = ConsentConfirmation.objects.get(confirmation_id=WRONG_CONFIRM_ID)
        redirect_url = '{}?process_id={}&success=false'.format(c.destination_endpoint_callback_url,
                                                               c.flow_request.process_id)
        fr = FlowRequest.objects.get(flow_id='12345')
        self.assertEquals(fr.status, FlowRequest.PENDING)

    # @patch('hgw_frontend.views.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    # @patch('hgw_frontend.views.KafkaProducer')
    # def test_confirm_add_flow_request_wrong_consent_status(self, mocked_kafka_producer):
    #     """
    #     Tests the behavior when a user try to call the /flow_requests/confirm view with no consent_confirm_id
    #     :return:
    #     """
    #     self.client.login(username='duck', password='duck')
    #     res = self.client.get('/v1/flow_requests/consents_confirmed/')
    #     self.assertEquals(res.status_code, 400)
    #     self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['INVALID_DATA'])
    #     fr = FlowRequest.objects.get(flow_id='12345')
    #     self.assertEquals(fr.status, FlowRequest.PENDING)

    @patch('hgw_frontend.views.flow_requests.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    @patch('hgw_frontend.views.flow_requests.KafkaProducer')
    def test_multiple_consent_confirms_request(self, mocked_kafka_producer):

        self.client.login(username='duck', password='duck')
        confirms_id = (CORRECT_CONFIRM_ID, CORRECT_CONFIRM_ID2)
        res = self.client.get(
            '/v1/flow_requests/consents_confirmed/?success=true&consent_confirm_id={}&consent_confirm_id={}'.format(
                *confirms_id))
        self.assertEquals(res.status_code, 302)

        for confirm_id in confirms_id:
            c = ConsentConfirmation.objects.get(confirmation_id=confirm_id)
            self.assertEquals(c.flow_request.status, FlowRequest.ACTIVE)

        redirect_url = '{}?process_id={}&success=true'.format(c.destination_endpoint_callback_url,
                                                              c.flow_request.process_id)
        self.assertRedirects(res, redirect_url, fetch_redirect_response=False)

    @patch('hgw_frontend.views.flow_requests.CONSENT_MANAGER_URI', CONSENT_MANAGER_URI)
    def test_confirm_add_flow_request_invalid_consent(self):
        """
        Tests the behavior when a user tries to call the /flow_requests/confirm view with a consent_confirm_id of an
        unknwon consent.
        :return:
        """
        self.client.login(username='duck', password='duck')
        res = self.client.get(
            '/v1/flow_requests/consents_confirmed/?success=true&consent_confirm_id={}'.format('aaaaa'))
        self.assertEquals(res.status_code, 400)
        self.assertEquals(res.content.decode('utf-8'), ERRORS_MESSAGE['INVALID_DATA'])

    def test_delete_flow_requests(self):
        headers = self._get_oauth_header()

        res = self.client.delete('/v1/flow_requests/54321/', **headers)
        self.assertEquals(res.status_code, 202)
        self.assertTrue('confirm_id' in res.json())
        self.assertEquals(FlowRequest.objects.all().count(), 2)
        self.assertEquals(FlowRequest.objects.get(process_id='54321').status, FlowRequest.DELETE_REQUESTED)

    def test_confirm_delete_flow_requests(self):
        headers = self._get_oauth_header()

        res = self.client.delete('/v1/flow_requests/54321/', **headers)

        # Then confirm the request
        confirm_id = res.json()['confirm_id']
        callback_url = 'http://127.0.0.1/'

        self.client.login(username='duck', password='duck')
        res = self.client.get('/v1/flow_requests/confirm/?confirm_id={}&callback_url={}&action=delete'.format(
            confirm_id,
            callback_url
        ))
        self.assertRedirects(res, callback_url, fetch_redirect_response=False)
        self.assertRaises(FlowRequest.DoesNotExist, FlowRequest.objects.get, process_id='54321')

    def test_get_flow_request_by_channel_id_with_super_client(self):
        """
        Tests functionality of getting the flow request by channel id, using a REST client with super client
        """
        # Gets the confirmation code installed with the test data
        c = ConsentConfirmation.objects.get(confirmation_id=CORRECT_CONFIRM_ID)
        self.client.get('/v1/flow_requests/confirm/?consent_confirm_id={}'.format(CORRECT_CONFIRM_ID))

        headers = self._get_oauth_header(client_index=2)
        res = self.client.get('/v1/flow_requests/search/?channel_id={}'.format(c.consent_id), **headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['process_id'], '54321')

    def test_get_flow_request_by_channel_id(self):
        """
        Tests that getting the flow request by channel id, using non admin REST client is forbidden
        """
        # Gets the confirmation code installed with the test data
        c = ConsentConfirmation.objects.get(confirmation_id=CORRECT_CONFIRM_ID)
        self.client.get('/v1/flow_requests/confirm/?consent_confirm_id={}'.format(CORRECT_CONFIRM_ID))

        headers = self._get_oauth_header()
        res = self.client.get('/v1/flow_requests/search/?channel_id={}'.format(c.consent_id), **headers)
        self.assertEqual(res.status_code, 403)

    def test_get_flow_request_by_channel_id_wrong_channel_id(self):
        # Gets the confirmation code installed with the test data
        c = ConsentConfirmation.objects.get(confirmation_id=CORRECT_CONFIRM_ID)
        self.client.get('/v1/flow_requests/confirm/?consent_confirm_id={}'.format(CORRECT_CONFIRM_ID))

        headers = self._get_oauth_header(client_index=2)
        res = self.client.get('/v1/flow_requests/search/?channel_id=unknown'.format(c.consent_id), **headers)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json(), {})

    def test_get_message(self):
        with patch('hgw_frontend.views.messages.KafkaConsumer', MockKafkaConsumer):
            self.set_mock_kafka_consumer(MockKafkaConsumer)
            headers = self._get_oauth_header(client_index=0)
            res = self.client.get('/v1/messages/3/', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()['message_id'], 3)
            res = self.client.get('/v1/messages/15/', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()['message_id'], 15)
            res = self.client.get('/v1/messages/32/', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()['message_id'], 32)

    def test_get_messages(self):
        with patch('hgw_frontend.views.messages.KafkaConsumer', MockKafkaConsumer):
            self.set_mock_kafka_consumer(MockKafkaConsumer)
            headers = self._get_oauth_header(client_index=0)
            res = self.client.get('/v1/messages/', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res['X-Total-Count'], '30')
            self.assertEqual(res['X-Skipped'], '0')
            self.assertEqual(len(res.json()), 5)

            res = self.client.get('/v1/messages/?start=6&limit=3', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 3)
            self.assertEqual(res['X-Total-Count'], '30')
            self.assertEqual(res['X-Skipped'], '3')
            self.assertEqual(res.json()[0]['message_id'], 6)
            self.assertEqual(res.json()[1]['message_id'], 7)
            self.assertEqual(res.json()[2]['message_id'], 8)

    def test_get_messages_max_limit(self):
        with patch('hgw_frontend.views.messages.KafkaConsumer', MockKafkaConsumer):
            self.set_mock_kafka_consumer(MockKafkaConsumer)
            headers = self._get_oauth_header(client_index=0)
            res = self.client.get('/v1/messages/?start=3&limit=11', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 10)
            self.assertEqual(res['X-Total-Count'], '30')
            self.assertEqual(res['X-Skipped'], '0')
            for i in range(3, 13):
                self.assertEqual(res.json()[i - 3]['message_id'], i)

    def test_get_message_not_found(self):
        with patch('hgw_frontend.views.messages.KafkaConsumer', MockKafkaConsumer):
            self.set_mock_kafka_consumer(MockKafkaConsumer)
            headers = self._get_oauth_header(client_index=0)
            res = self.client.get('/v1/messages/33/', **headers)
            self.assertEqual(res.status_code, 404)
            self.assertDictEqual(res.json(), {'first_id': 3, 'last_id': 32})

            res = self.client.get('/v1/messages/0/', **headers)
            self.assertEqual(res.status_code, 404)
            self.assertDictEqual(res.json(), {'first_id': 3, 'last_id': 32})

    def test_get_messages_not_found(self):
        with patch('hgw_frontend.views.messages.KafkaConsumer', MockKafkaConsumer):
            self.set_mock_kafka_consumer(MockKafkaConsumer)
            headers = self._get_oauth_header(client_index=0)
            res = self.client.get('/v1/messages/?start=30&limit=5', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 3)
            self.assertEqual(res['X-Skipped'], '27')
            self.assertEqual(res['X-Total-Count'], '30')

            res = self.client.get('/v1/messages/?start=0&limit=5', **headers)
            self.assertEqual(res.status_code, 404)
            self.assertDictEqual(res.json(), {'first_id': 3, 'last_id': 32})

    def test_get_messages_info(self):
        with patch('hgw_frontend.views.messages.KafkaConsumer', MockKafkaConsumer):
            self.set_mock_kafka_consumer(MockKafkaConsumer)
            headers = self._get_oauth_header(client_index=0)
            res = self.client.get('/v1/messages/info/', **headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {
                'start_id': 3,
                'last_id': 32,
                'count': 30
            })

    def test_rest_forbidden(self):
        """
        Tests that accessing via REST is forbidden for a client configured using kafka
        :return:
        """
        with patch('hgw_frontend.views.messages.KafkaConsumer', MockKafkaConsumer):
            self.set_mock_kafka_consumer(MockKafkaConsumer)
            headers = self._get_oauth_header(client_index=1)
            res = self.client.get('/v1/messages/3/', **headers)
            self.assertEqual(res.status_code, 403)
            res = self.client.get('/v1/messages/', **headers)
            self.assertEqual(res.status_code, 403)
            res = self.client.get('/v1/messages/info/', **headers)
            self.assertEqual(res.status_code, 403)