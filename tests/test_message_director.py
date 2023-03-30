import unittest

from otp.networking import DownstreamClient, CarsProtocol

class TestProtocol(CarsProtocol):
    pass

class TestClient(DownstreamClient):
    upstreamProtocol = TestProtocol

class TestMessageDirector(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()
