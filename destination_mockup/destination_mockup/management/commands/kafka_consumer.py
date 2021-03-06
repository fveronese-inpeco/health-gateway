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
import os
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand
from kafka import KafkaConsumer, TopicPartition
from hgw_common.cipher import Cipher
from Cryptodome.PublicKey import RSA

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "destination_mockup.settings")

MAGIC_BYTES = '\xdf\xbb'


class Command(BaseCommand):
    PRI_RSA_KEY_PATH = os.path.join(settings.BASE_DIR, 'certs/kafka/payload_encryption/private_key.pem')

    help = 'Launch the kafka consumer '

    def __init__(self):
        with open(self.PRI_RSA_KEY_PATH, 'r') as f:
            self.rsa_pri_key = RSA.importKey(f.read())
            self.cipher = Cipher(private_key=self.rsa_pri_key)
        super(Command, self).__init__()

    def _handle_payload(self, data, *args, **options):
        docs = json.loads(data)
        print('\nFound documents for {} person(s)'.format(len(docs)))

        unique_filename = str(uuid.uuid4())
        try:
            os.mkdir('/tmp/msgs/')
        except OSError:
            pass
        with open('/tmp/msgs/{}'.format(unique_filename), 'w') as f:
            f.write(data)

    def handle(self, *args, **options):
        kc = KafkaConsumer(bootstrap_servers=settings.KAFKA_BROKER,
                           client_id=settings.DESTINATION_ID,
                           group_id=settings.DESTINATION_ID,
                           security_protocol='SSL',
                           ssl_check_hostname=True,
                           ssl_cafile=settings.KAFKA_CA_CERT,
                           ssl_certfile=settings.KAFKA_CLIENT_CERT,
                           ssl_keyfile=settings.KAFKA_CLIENT_KEY)
        kc.subscribe([settings.KAFKA_TOPIC])
        print('Starting to receive messages for topic: {}'.format(settings.KAFKA_TOPIC))
        for msg in kc:
            headers = dict(msg.headers)
            print("Received message with process_id %s, channel_id %s, source_id %s, and id %s",
                  headers['process_id'], headers['channel_id'], headers['source_id'], msg.offset)
            message = msg.value
            if self.cipher.is_encrypted(message):
                self._handle_payload(self.cipher.decrypt(message), *args, **options)
            else:
                self._handle_payload(message.decode("utf-8"), *args, **options)


if __name__ == '__main__':
    c = Command()
    c.handle()
