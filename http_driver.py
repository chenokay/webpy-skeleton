#!/usr/bin/env python
# coding: utf-8
import httplib
import sys
import os
import config
import sys

class HttpDriver():

    def __init__(self, host, logger):
        self.http_handle = httplib.HTTPConnection(host=host, port=80, timeout=10)
        self.retry_times = 3
        self.logger = logger

    def get(self, path):
        try:
            for i in xrange(self.retry_times):
                self.http_handle.connect()

                self.http_handle.request('GET', path)
                res = self.http_handle.getresponse()

                if 200 != res.status:
                    self.http_handle.close()
                    continue

                body = res.read()
                self.http_handle.close()

                return body, "SUCC"
            return None, 'FAILURE'
        except Exception, why:
            self.http_handle.close()
            return None, "exception[%s]" %(why)

if __name__ == '__main__':
    hd = HttpDriver('apistore.baidu.com', config.logger)
    print hd.get('/microservice/iplookup?ip=211.100.31.74')
