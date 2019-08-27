
import os
import pdb
import treq

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

        text = exc.__repr__()

        # Asterisks for <b></b>
        # Double line feed for newline
        if 'ResponseNeverReceived' in text:
            text = '*TimeoutError*'
        elif 'ConnectionRefusedError' in text:
            text = '*ConnectionRefusedError*'

        payload = {'text': text,
                   'username': 'arscca-twisted',
                   'icon_emoji': ':ghost:'}

        # Using treq instead of requests
        # Note in this case it has the same signature
        deferred = treq.post(url, json=payload, timeout=5)


if __name__ == '__main__':
    class TestException(Exception):
        '''Testing Slack Hook'''

    exc = TestException('Sending into orbit')
    Util.post_to_slack(exc)

    from twisted.internet import reactor
    reactor.run()
    print('CTRL-C to stop reactor')

