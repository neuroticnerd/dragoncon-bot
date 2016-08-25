# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import json
import logging
import uuid

from collections import OrderedDict
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from armory.phone import phone
from armory.serialize import jsonify

from jinja2 import Environment, PackageLoader

log = logging.getLogger(__name__)


class CommProxy(object):
    COMM_CONFIG_FILE = '.commconfig'
    DEFAULT_EMAIL_SUBJECT = 'Dragon Con Alert: Host Hotel Availability'
    DEFAULT_MMS_SUBJECT = 'Dragon Con Alert'

    def __init__(self, config=None, send_email=True, send_sms=True, **kwargs):
        if config is None:
            config = self.COMM_CONFIG_FILE
        self.conf = kwargs['settings']
        self.send_sms = self.conf.sms_enabled
        self.send_email = self.conf.email_enabled
        self._gateway = None

        try:
            with io.open(config, 'r', encoding='utf-8') as f:
                config_raw = f.read()
                commdata = json.loads(
                    config_raw, object_pairs_hook=OrderedDict
                )
        except OSError:
            warning_message = '{0} configuration file could not be accessed.'
            log.warning(warning_message.format(config))
            commdata = {}

        self.commdata = commdata
        self._smtp_login = commdata.get('smtp_login', {})
        self._sms_gateways = commdata.get('sms_gateways', {})
        self._lookups = commdata.get('lookups', {})
        self.recipients = [
            self._lookups.get(to) for to in commdata.get('recipients', [])
        ]

        self._jinja = Environment(
            loader=PackageLoader('dragonite', 'templates')
        )
        self.sms_template = self._jinja.get_template('sms_template.j2')
        self.email_template = self._jinja.get_template('email_template.j2')
        self._email_subject = kwargs.get('subject', self.DEFAULT_EMAIL_SUBJECT)
        self._mms_subject = kwargs.get('mms_subject', self.DEFAULT_MMS_SUBJECT)

    def __enter__(self):
        if self._gateway is None:
            self._gateway = phone.EmailSMS(**self._smtp_login)
        self.gateway = self._gateway.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.gateway.__exit__(exc_type, exc_value, exc_traceback)
        self.gateway = None

    @property
    def email_subject(self):
        if self.conf.debug:
            return '***TEST*** ' + self._email_subject
        return self._email_subject

    @property
    def mms_subject(self):
        if self.conf.debug:
            return '***TEST*** ' + self._mms_subject
        return self._mms_subject

    def notify(self, data_object, ref_uuid=None):
        """
        Sends SMS/MMS and email messages based on settings.

        :param data_object: contains the results triggering the messages
        :type data_object: dragonite.scrapers.base.ScrapeResults
        :param ref_uuid: the UUID of the scrape for reference if needed
        :type ref_uuid: uuid.UUID or a str UUID

        NOTE: SMS/MMS messages do not appear to work properly unless
        sent to the gateway as a multipart/mixed email.

        NOTE: SMS messages can only be up to 160 characters; it needs to
        use an MMS gateway if it is longer than that limit.
        """
        alert_uuid = str(ref_uuid) if ref_uuid else uuid.uuid4().hex
        log.debug('notify UUID={0}'.format(alert_uuid))

        template_variables = {
            'to_name': ', '.join(
                [to['first_name'] for to in self.recipients]
            ),
            'hotel': {
                'name': data_object.parent.friendly,
                'phone': data_object.parent.phone,
                'phone': data_object.parent.phone,
                'link': data_object.parent.link,
                'rooms': '<unknown>',
            },
            'debug_test': self.conf.debug,
            'alert_uuid': alert_uuid,
        }
        if hasattr(self.conf, 'inject_message'):
            template_variables['inject_message'] = self.conf.inject_message

        if self.send_email:
            cookies = json.dumps(
                data_object.session.cookies.get_dict(),
                indent=2
            )
            to_list = [to['email'] for to in self.recipients]

            email = MIMEMultipart(_subtype='mixed')
            email['subject'] = self.email_subject
            email['to'] = ', '.join(to_list)
            email['from'] = self.gateway._sender
            email['sender'] = 'dragonite@neuroticnerd.com'
            email['reply-to'] = ', '.join(to_list)

            body_text_plain = self.email_template.render(
                render_html=False,
                **template_variables
            )
            body_text_html = self.email_template.render(
                render_html=True,
                **template_variables
            )
            email_body = MIMEMultipart(_subtype='alternative')
            email_body.attach(MIMEText(body_text_plain, _subtype='plain'))
            email_body.attach(MIMEText(body_text_html, _subtype='html'))
            email.attach(email_body)

            raw_response = MIMEText(data_object.raw, _subtype='html')
            raw_response.add_header(
                'Content-Disposition',
                'attachment',
                filename='raw_response.html'
            )
            email.attach(raw_response)

            cookies = MIMEApplication(cookies, _subtype='json')
            cookies.add_header(
                'Content-Disposition',
                'attachment',
                filename='cookies.json'
            )
            email.attach(cookies)

            config = MIMEApplication(
                self.conf.dumps(pretty=True), _subtype='json'
            )
            config.add_header(
                'Content-Disposition',
                'attachment',
                filename='settings.json'
            )
            email.attach(config)

            self.gateway.send(to_list, email.as_string())
            log.debug((
                '*************************\n'
                'email sent to {0}:\n\n{1}'
            ).format(template_variables['to_name'], email.as_string()))

        if self.send_sms:
            message_text = self.sms_template.render(**template_variables)
            message_length = len(message_text)
            if message_length < 160:
                message_type = 'sms'
            else:
                message_type = 'mms'
            message = MIMEMultipart(_subtype='mixed')
            if message_type == 'mms':
                message['subject'] = self.mms_subject
            message.attach(MIMEText(message_text, _subtype='plain'))
            for to in self.recipients:
                self.gateway.send(to[message_type], message.as_string())
                log.debug((
                    '*************************\n'
                    '{0} sent to {1}:\n\n{2}'
                ).format(
                    message_type.upper(),
                    to['comment'],
                    message.as_string()
                ))

    def dumps(self, constrain=None, pretty=False):
        info = OrderedDict()
        if constrain is None or constrain == 'smtp':
            info['smtp_server'] = self.commdata['smtp_login']['server']
            info['smtp_username'] = self.commdata['smtp_login']['username']
        if constrain is None or constrain == 'lookups':
            lookinfo = []
            for key in self.commdata['lookups']:
                person = self.commdata['lookups'][key]
                lookinfo.append('{0:8}  {1}  {2}'.format(
                    person['first_name'],
                    person['phone'],
                    person['email']
                ))
            info = lookinfo
        if constrain is None or constrain == 'recipients':
            info = self.commdata['recipients']
        return jsonify(info, pretty=pretty)
