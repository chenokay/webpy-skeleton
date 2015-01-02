# -*- coding: UTF-8 -*-
from collections import defaultdict

import web

import config
import model as m
import sys
import http_driver 
import json

reload(sys)
sys.setdefaultencoding('utf-8')


VERSION = "0.0.1"

urls = (
    r'/', 'Index',
    )

app = web.application(urls, globals())

# Allow session to be reloadable in development mode.
if web.config.get('_session') is None:
    session = web.session.Session(app, web.session.DiskStore('sessions'),
                                  initializer={'flash': defaultdict(list)})

    web.config._session = session
else:
    session = web.config._session


def flash(group, message):
    session.flash[group].append(message)


def flash_messages(group=None):
    if not hasattr(web.ctx, 'flash'):
        web.ctx.flash = session.flash
        session.flash = defaultdict(list)
    if group:
        return web.ctx.flash.get(group, [])
    else:
        return web.ctx.flash

render = web.template.render('templates/',
                             base='base',
                             cache=config.cache)
t_globals = web.template.Template.globals
t_globals['datestr'] = web.datestr
t_globals['app_version'] = lambda: VERSION + ' - ' + config.env
t_globals['flash_messages'] = flash_messages
t_globals['render'] = lambda t, *args: render._template(t)(*args)


class Index:
    def __init__(self):
        self.ip2region = "/microservice/iplookup?ip="
        self.region2code = "/microservice/cityinfo?cityname="
        self.code2weather = "/microservice/weather?cityid="
        self.region2aqi = "/microservice/aqi?city="

        self.http_handle=http_driver.HttpDriver('apistore.baidu.com', config.logger)

        self.ip = '127.0.0.1'
        self.region = ''
        self.regioncode = ''
        self.weather = ''
        self.centigrade = ''
        self.wind = ''

        self.aqi = ''
        self.level = ''

    def get_region(self, ip):
        ip2region_path = self.ip2region
        ip2region_path = ip2region_path + ip
        ret = self.http_handle.get(ip2region_path)
        if ret[1] != 'SUCC':
            return ''
        kv = json.loads(ret[0])

        if 'retData' in kv:
            if 'city' in kv['retData']:
                ## discard the last chinese character
                return kv['retData']['city'][:-1]
    
        return ''

    def get_aqi(self):
        region2aqi_path = self.region2aqi
        region2aqi_path = region2aqi_path + self.region

        ret = self.http_handle.get(region2aqi_path)

        if ret[1] != 'SUCC':
            return ''

        kv = json.loads(ret[0])

        if 'retData' in kv:
            if 'aqi' in kv['retData']:
                self.aqi = kv['retData']['aqi']
            if 'level' in kv['retData']:
                self.level = kv['retData']['level']

            return str(self.aqi) + str(self.level)

        else:
            return ''

    def get_region_code(self):
        region2code_path = self.region2code
        region2code_path = region2code_path  + self.region

        ret = self.http_handle.get(region2code_path)

        if ret[1] != 'SUCC':
            return ''

        kv = json.loads(ret[0])

        if 'retData' in kv:
            if 'cityCode' in kv['retData']:
                return kv['retData']['cityCode']

        return ''

    def get_weather(self):
        city2weather_path = self.code2weather
        city2weather_path = city2weather_path + self.regioncode

        ret = self.http_handle.get(city2weather_path)
        if ret[1] != 'SUCC':
            return ''

        kv = json.loads(ret[0])

        if 'retData' in kv:
            if 'weather' in kv['retData']:
                self.weather = kv['retData']['weather']
            if 'l_tmp' in kv['retData'] and 'h_tmp' in kv['retData']:
                self.centigrade = '%s - %s' %(kv['retData']['l_tmp'], kv['retData']['h_tmp'])
            if 'WD' in kv['retData'] and 'WS' in kv['retData']:
                self.wind = '%s %s' %(kv['retData']['WD'], kv['retData']['WS'])

            return str(self.weather) + str(self.centigrade) + str(self.wind)

        return ''

    def get_env(self):
        region = self.get_region(self.ip)
        if region != '':
            self.region = region
        else:
            return 'FAIL TO GET REGION'

        regioncode = self.get_region_code()
        if regioncode != '':
            self.regioncode = regioncode
        else:
            return 'FAIL TO GET CITYCODE'
        
        weather = self.get_weather()
        if weather == '':
            return 'FAIL TO GET WEATHER'

        aqi = self.get_aqi()

        if aqi == '':
            return 'FAIL TO GET AQI'

        return 'OK'
        
    def GET(self):
        #flash("success", """Welcome! Application code lives in app.py,
        #models in model.py, tests in test.py, and seed data in seed.py.""")
        self.ip = web.ctx['ip']
        ret = self.get_env()

        region = '北京'
        weather = '晴'
        aqi = '良'
        if 'OK' != ret:
            config.logger.warn('fail to init environment [%s][%s]', self.ip, ret)
        else:
            region = self.region
            weather = self.weather + ' ' + self.centigrade
            aqi = str(self.aqi) + ' ' + self.level + '   ' + self.wind 
            
        return render.index(region, weather, aqi)


# Set a custom internal error message
def internalerror():
    msg = """
    An internal server error occurred. Please try your request again by
    hitting back on your web browser. You can also <a href="/"> go back
     to the main page.</a>
    """
    return web.internalerror(msg)


# Setup the application's error handler
app.internalerror = web.debugerror if web.config.debug else internalerror

if config.email_errors.to_address:
    app.internalerror = web.emailerrors(config.email_errors.to_address,
                                        app.internalerror,
                                        config.email_errors.from_address)


# Adds a wsgi callable for uwsgi
application = app.wsgifunc()
if __name__ == "__main__":
    app.run()
