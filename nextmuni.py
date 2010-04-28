__author__ = 'Jeremy Latt <jeremy.latt@gmail.com>'

import datetime
import urllib
import urlparse

from lxml import etree

class RouteSummary(object):
    def __init__(self, el):
        self.tag = el.get('tag')
        self.title = el.get('title')
        self.short_title = el.get('shortTitle') or self.title

    __str__ = lambda self: self.title

    __repr__ = lambda self: 'RouteSummary(tag=%(tag)s, title=%(title)s)' % self.__dict__

class Point(object):
    def __init__(self, el):
        self.lat = float(el.get('lat'))
        self.lon = float(el.get('lon'))

    __repr__ = lambda self: 'Point(lat=%(lat)f, lon=%(lon)f)' % self.__dict__

    __str__ = __repr__

class Stop(Point):
    def __init__(self, el):
        self.tag = el.get('tag')
        self.title = el.get('title')
        self.short_title = el.get('shortTitle') or self.title
        self.id = el.get('stopId')
        super(Stop, self).__init__(el)

    __str__ = lambda self: self.id

    __repr__ = lambda self: 'Stop(tag=%(tag)s, title=%(title)s, id=%(id)s)' % self.__dict__

class Direction(object):
    def __init__(self, el, id_to_stop):
        self.tag = el.get('tag')
        self.title = el.get('title')
        self.use_for_ui = el.get('useForUI') == 'true'
        self.stops = [id_to_stop[stop.get('tag')] for stop in el.xpath('stop')]

    __str__ = lambda self: self.title

    __repr__ = lambda self: 'Direction(tag=%(tag)s, title=%(title)s)' % self.__dict__

class Path(object):
    def __init__(self, el):
        self.points = map(Point, el.xpath('point'))

    __str__ = lambda self: str(self.points)

    __repr__ = __str__
        
class Route(object):
    def __init__(self, el):
        self.tag = el.get('tag')
        self.code = el.get('routeCode')
        self.title = el.get('title')
        self.short_title = el.get('shortTitle') or self.title
        self.color = el.get('color')
        self.opposite_color = el.get('oppositeColor')

        self.stops = map(Stop, el.xpath('stop'))
        tag_to_stop = dict((stop.tag, stop) for stop in self.stops)
        self.directions = [Direction(el, tag_to_stop) for el in el.xpath('direction')]
        self.paths = map(Path, el.xpath('path'))

    __str__ = lambda self: 'Route(tag=%(tag)s, title=%(title)s)' % self.__dict__

    __repr__ = __str__

class Prediction(object):
    def __init__(self, el):
        self.seconds = int(el.get('seconds'))
        self.minutes = int(el.get('minutes'))
        self.epoch_time = epoch_time_to_datetime(el.get('epochTime'))
        self.is_departure = el.get('isDeparture') == 'true'
        self.dir_tag = el.get('dirTag')
        self.block = el.get('block')

    __str__ = lambda self: str(self.minutes)

    __repr__ = lambda self: 'Prediction(minutes=%(minutes)d, is_departure=%(is_departure)s)' % self.__dict__

class Predictions(object):
    def __init__(self, el):
        self.directions = dict((d.get('title'), map(Prediction, d.xpath('prediction'))) for d in el.xpath('direction'))
        self.messages = [msg.get('text') for msg in el.xpath('message')]

    __str__ = lambda self: str(self.directions)

    __repr__ = __str__

class Vehicle(Point):
    def __init__(self, el):
        self.id = el.get('id')
        self.route_tag = el.get('routeTag')
        self.dir_tag = el.get('dirTag')
        self.secs_since_report = int(el.get('secsSinceReport'))
        self.predictable = el.get('predictable') == 'true'
        self.heading = int(el.get('heading'))
        super(Vehicle, self).__init__(el)

    __repr__ = lambda self: 'Vehicle(id=%(id)s, route=%(route_tag)s, dir=%(dir_tag)s, lat=%(lat)f, lon=%(lon)f)' % self.__dict__
    
    __str__ = __repr__

base_url = 'http://webservices.nextbus.com/service/publicXMLFeed'
agency_param = 'sf-muni' # a
epoch = datetime.datetime.utcfromtimestamp(0)

def feed_url(*pairs, **params):
    pairs = list(pairs)
    params['a'] = agency_param
    pairs.extend(params.items())
    url = base_url + '?' + urllib.urlencode(pairs, doseq=True)
    return url

def feed_doc(*args, **kw):
    url = feed_url(*args, **kw)
    resource = urllib.urlopen(url)
    doc = etree.parse(resource)
    return doc

def epoch_time_to_datetime(epoch_time):
    return datetime.datetime.utcfromtimestamp(int(epoch_time) / 1000.0)

def route_list():
    doc = feed_doc(command='routeList')
    route_elements = doc.xpath('/body/route')
    routes = map(RouteSummary, route_elements)
    return routes

def route_config(tag=None):
    params = {'command': 'routeConfig'}
    if tag:
        params['r'] = tag
    doc = feed_doc(**params)
    route_elements = doc.xpath('/body/route')
    routes = map(Route, route_elements)
    return routes[0] if tag else routes

def predictions_for_stop(stop_id):
    doc = feed_doc(command='predictions', stopId=stop_id)
    predictions = Predictions(doc.xpath('/body/predictions')[0])
    return predictions

def predictions_for_stops(route_stop_pairs):
    '''broken'''
    doc = feed_doc(command='predictionsForMultiStops', *[('stops', '|null|'.join(pair)) for pair in route_stop_pairs])
    predictionses = map(Predictions, doc.xpath('/body/predictions'))
    return predictionses

def vehicle_locations(route, last_time=None):
    t = 0
    if last_time:
        delta = last_time - epoch
        t += delta.days * 24 * 60 * 60 * 1000
        t += delta.seconds * 1000
        t += delta.microseconds / 1000

    doc = feed_doc(command='vehicleLocations', r=route, t=t)
    last_time = epoch_time_to_datetime(doc.xpath('lastTime')[0].get('time'))
    vehicles = map(Vehicle, doc.xpath('/body/vehicle'))
    return vehicles, last_time

if __name__ == '__main__':
    import pprint
    vehicles, last_time = vehicle_locations('38')
    pprint.pprint(vehicles)
    pprint.pprint(last_time)
