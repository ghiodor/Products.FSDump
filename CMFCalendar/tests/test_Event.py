from unittest import TestCase, TestSuite, makeSuite, main

import Testing
import Zope
try:
    Zope.startup()
except AttributeError:
    # for Zope versions before 2.6.1
    pass

from DateTime import DateTime

from Products.CMFCalendar.Event import Event
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.dummy import DummyTool


class TestEvent(TestCase):

    def setUp(self):
        self.site = DummySite('site')
        self.site._setObject( 'portal_membership', DummyTool() )

    def test_new(self):
        event = Event('test')
        assert event.getId() == 'test'
        assert not event.Title()

    def test_edit(self):
        event = self.site._setObject( 'testimage', Event('editing') )
        event.edit( title='title'
                  , description='description'
                  , eventType=( 'eventType', )
                  , effectiveDay=1
                  , effectiveMo=1
                  , effectiveYear=1999
                  , expirationDay=12
                  , expirationMo=31
                  , expirationYear=1999
                  , start_time="00:00"
                  , startAMPM="AM"
                  , stop_time="11:59"
                  , stopAMPM="PM"
                  )
        assert event.Title() == 'title'
        assert event.Description() == 'description'
        assert event.Subject() == ( 'eventType', ), event.Subject()
        assert event.effective_date == None
        assert event.expiration_date == None
        assert event.end() == DateTime('1999/12/31 23:59')
        assert event.start() == DateTime('1999/01/01 00:00')
        assert not event.contact_name

    def test_puke(self):
        event = Event( 'shouldPuke' )
        self.assertRaises( DateTime.DateError
                         , event.edit
                         , effectiveDay=31
                         , effectiveMo=2
                         , effectiveYear=1999
                         , start_time="00:00"
                         , startAMPM="AM"
                         )


def test_suite():
    return TestSuite((
        makeSuite(TestEvent),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
