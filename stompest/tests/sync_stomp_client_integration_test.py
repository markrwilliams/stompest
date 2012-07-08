"""
Copyright 2011 Mozes, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import logging
import time
import unittest

from stompest.error import StompConnectionError
from stompest.sync import Stomp

logging.basicConfig(level=logging.DEBUG)

class SimpleStompIntegrationTest(unittest.TestCase):
    DEST = '/queue/stompUnitTest'
    
    def setUp(self):
        stomp = Stomp('tcp://localhost:61613')
        stomp.connect()
        stomp.subscribe(self.DEST, {'ack': 'client'})
        while stomp.canRead(1):
            stomp.ack(stomp.receiveFrame())
        stomp.disconnect()

    def test_1_integration(self):
        stomp = Stomp('tcp://localhost:61613')
        stomp.connect()
        stomp.send(self.DEST, 'test message 1')
        stomp.send(self.DEST, 'test message 2')
        self.assertFalse(stomp.canRead(1))
        stomp.subscribe(self.DEST, {'ack': 'client'})
        self.assertTrue(stomp.canRead(1))
        stomp.ack(stomp.receiveFrame())
        self.assertTrue(stomp.canRead(1))
        stomp.ack(stomp.receiveFrame())
        self.assertFalse(stomp.canRead(1))
        stomp.disconnect()

    def test_2_timeout(self):
        timeout = 150
        tolerance = .005
        initialReconnectDelay = .01
        
        stomp = Stomp('failover:(tcp://localhost:61614,tcp://localhost:61615)?startupMaxReconnectAttempts=2,backOffMultiplier=3')
        expectedTimeout = time.time() + 40 / 1000.0 # 40 ms = 10 ms + 3 * 10 ms
        self.assertRaises(StompConnectionError, stomp.connect)
        self.assertTrue(abs(time.time() - expectedTimeout) < initialReconnectDelay)
        
        stomp = Stomp('failover:(tcp://localhost:61614,tcp://localhost:61615)?startupMaxReconnectAttempts=5,maxReconnectDelay=%d,useExponentialBackOff=false,initialReconnectDelay=30,reconnectDelayJitter=5' % timeout)
        expectedTimeout = time.time() + timeout / 1000.0
        self.assertRaises(StompConnectionError, stomp.connect)
        self.assertTrue(abs(time.time() - expectedTimeout) < tolerance)

        stomp = Stomp('failover:(tcp://localhost:61614,tcp://localhost:61613)?randomize=false') # default is startupMaxReconnectAttempts = 0
        expectedTimeout = time.time() + 0
        self.assertRaises(StompConnectionError, stomp.connect)
        self.assertTrue(abs(time.time() - expectedTimeout) < initialReconnectDelay)

        stomp = Stomp('failover:(tcp://localhost:61614,tcp://localhost:61613)?startupMaxReconnectAttempts=1,randomize=false')
        stomp.connect()
        stomp.disconnect()
    
    def test_3_socket_failure_and_replay(self):
        stomp = Stomp('tcp://localhost:61613')
        stomp.connect()
        stomp.send(self.DEST, 'test message 1')
        stomp.subscribe(self.DEST, {'ack': 'client'})
        self.assertEqual(stomp._subscriptions, [(self.DEST, (('ack', 'client'),))])
        stomp._stomp.socket.close()
        self.assertRaises(StompConnectionError, stomp.receiveFrame)
        stomp.connect()
        stomp.ack(stomp.receiveFrame())
        stomp.disconnect()

if __name__ == '__main__':
    unittest.main()