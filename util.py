
import os
import pdb
import requests

class Util():

    HOST = 'localhost'
    PORT = '6543'

    @classmethod
    def post_to_slack(cls, exc):
        url = os.environ.get('ARSCCA_TWISTED_SLACK_HOOK')
        if not url:
            print(f'ERROR: {exc}')
            print('NOT POSTING TO SLACK because no URL provided')
            return

        exception_name = exc.__class__.__name__
        # Asterisks are like <b></b>

        # Double line feed for newline
        # Asterisk for <b></b>
        payload = {'text': exc.__repr__(),
                   'username': 'RacecarBot',
                   'icon_emoji': ':ghost:'}

        requests.post(url, json=payload, timeout=1)
        1


if __name__ == '__main__':
    class TestException(Exception):
        '''Testing Slack Hook'''

    exc = TestException('Sending into orbit')
    Util.post_to_slack(exc)

