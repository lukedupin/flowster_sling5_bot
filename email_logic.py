import settings

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId, SendAt
#from python_http_client import BadRequestsError, UnauthorizedError, ForbiddenError

import re, random, base64, uuid, datetime
from email.utils import parseaddr


def raw_email(to_email, subject, body, from_email=None, cc_email=None):
    if from_email is None:
        from_email = f'Sling5  <info@sling5.io>'

    # to_email could be a single string or a list of strings
    if isinstance(to_email, list):
        for email in to_email:
            if email.find('@') < 0:
                return None
    else:
        if to_email.find('@') < 0:
            return None

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=body)

    if cc_email is not None:
        message.add_cc(cc_email)

    # response = None
    try:
        sg = SendGridAPIClient(settings.SEND_GRID['API_KEY'])
        response = sg.send(message)
        # print(response.status_code)
        # print(response.body)
        # print(response.headers)
    except KeyError as e:
        return "Invalid API key!"
    except Exception as e:
        return f"Bad request for email: {to_email}"

    return None
