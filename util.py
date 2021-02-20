"""
Module containing Util class
"""
import os
import treq


# pylint: disable=too-few-public-methods
class Util:
    """
    Utility methods that may be used through the project
    """

    @classmethod
    def post_to_slack(cls, exc):
        """
        Post an exception to slack
        """
        url = os.environ.get('ARSCCA_TWISTED_SLACK_HOOK')
        if url:
            print(f'ERROR: {exc}')
            print(f'Posting to Slack: {url}')
        else:
            print(f'ERROR: {exc}')
            print('NOT POSTING TO SLACK because no URL provided')
            return

        text = exc.__repr__()

        # Asterisks for <b></b>
        # Double line feed for newline
        if 'ResponseNeverReceived' in text:
            text = '*TimeoutError*'
        elif 'ConnectionRefusedError' in text:
            text = '*ConnectionRefusedError*'

        payload = {'text': text, 'username': 'arscca-twisted', 'icon_emoji': ':ghost:'}

        # Using treq instead of requests
        # Note in this case it has the same signature
        treq.post(url, json=payload, timeout=5)


if __name__ == '__main__':

    class TestException(Exception):
        '''Testing Slack Hook'''

    test_exc = TestException('Sending into orbit')
    Util.post_to_slack(test_exc)

    from twisted.internet import reactor

    # pylint: disable=no-member
    reactor.run()
    print('CTRL-C to stop reactor')
