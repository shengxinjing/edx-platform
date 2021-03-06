"""Test Entitlements models"""

import unittest
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.test import TestCase

from certificates.models import CertificateStatuses  # pylint: disable=import-error
from lms.djangoapps.certificates.api import MODES
from lms.djangoapps.certificates.tests.factories import GeneratedCertificateFactory
from openedx.core.djangoapps.content.course_overviews.tests.factories import CourseOverviewFactory
from student.tests.factories import CourseEnrollmentFactory

# Entitlements is not in CMS' INSTALLED_APPS so these imports will error during test collection
if settings.ROOT_URLCONF == 'lms.urls':
    from entitlements.tests.factories import CourseEntitlementFactory


@unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
class TestModels(TestCase):
    """Test entitlement with policy model functions."""

    def setUp(self):
        super(TestModels, self).setUp()
        self.course = CourseOverviewFactory.create(
            start=datetime.utcnow()
        )
        self.enrollment = CourseEnrollmentFactory.create(course_id=self.course.id)

    def test_is_entitlement_redeemable(self):
        """
        Test that the entitlement is not expired when created now, and is expired when created 2 years
        ago with a policy that sets the expiration period to 450 days
        """

        entitlement = CourseEntitlementFactory.create()

        assert entitlement.is_entitlement_redeemable() is True

        # Create a date 2 years in the past (greater than the policy expire period of 450 days)
        past_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=365 * 2)
        entitlement.created = past_datetime
        entitlement.save()

        assert entitlement.is_entitlement_redeemable() is False

    def test_is_entitlement_refundable(self):
        """
        Test that the entitlement is refundable when created now, and is not refundable when created 70 days
        ago with a policy that sets the expiration period to 60 days. Also test that if the entitlement is spent
        and greater than 14 days it is no longer refundable.
        """
        entitlement = CourseEntitlementFactory.create()
        assert entitlement.is_entitlement_refundable() is True

        # If there is no order_number make sure the entitlement is not refundable
        entitlement.order_number = None
        assert entitlement.is_entitlement_refundable() is False

        # Create a date 70 days in the past (greater than the policy refund expire period of 60 days)
        past_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=70)
        entitlement = CourseEntitlementFactory.create(created=past_datetime)

        assert entitlement.is_entitlement_refundable() is False

        entitlement = CourseEntitlementFactory.create(enrollment_course_run=self.enrollment)
        # Create a date 20 days in the past (less than the policy refund expire period of 60 days)
        # but more than the policy regain period of 14 days and also the course start
        past_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=20)
        entitlement.created = past_datetime
        self.enrollment.created = past_datetime
        self.course.start = past_datetime
        entitlement.save()
        self.course.save()
        self.enrollment.save()

        assert entitlement.is_entitlement_refundable() is False

        # Removing the entitlement being redeemed, make sure that the entitlement is refundable
        entitlement.enrollment_course_run = None

        assert entitlement.is_entitlement_refundable() is True

    def test_is_entitlement_regainable(self):
        """
        Test that the entitlement is not expired when created now, and is expired when created20 days
        ago with a policy that sets the expiration period to 14 days
        """
        entitlement = CourseEntitlementFactory.create(enrollment_course_run=self.enrollment)
        assert entitlement.is_entitlement_regainable() is True

        # Create and associate a GeneratedCertificate for a user and course and make sure it isn't regainable
        GeneratedCertificateFactory(
            user=entitlement.user,
            course_id=entitlement.enrollment_course_run.course_id,
            mode=MODES.verified,
            status=CertificateStatuses.downloadable,
        )

        assert entitlement.is_entitlement_regainable() is False

        # Create a date 20 days in the past (greater than the policy expire period of 14 days)
        # and apply it to both the entitlement and the course
        past_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=20)
        entitlement = CourseEntitlementFactory.create(enrollment_course_run=self.enrollment, created=past_datetime)
        self.enrollment.created = past_datetime
        self.course.start = past_datetime

        self.course.save()
        self.enrollment.save()

        assert entitlement.is_entitlement_regainable() is False

    def test_get_days_until_expiration(self):
        """
        Test that the expiration period is always less than or equal to the policy expiration
        """
        entitlement = CourseEntitlementFactory.create(enrollment_course_run=self.enrollment)
        # This will always either be 1 less than the expiration_period_days because the get_days_until_expiration
        # method will have had at least some time pass between object creation in setUp and this method execution,
        # or the exact same as the original expiration_period_days if somehow no time has passed
        assert entitlement.get_days_until_expiration() <= entitlement.policy.expiration_period.days

    def test_expired_at_datetime(self):
        """
        Tests that using the getter method properly updates the expired_at field for an entitlement
        """

        # Verify a brand new entitlement isn't expired and the db row isn't updated
        entitlement = CourseEntitlementFactory.create()
        expired_at_datetime = entitlement.expired_at_datetime
        assert expired_at_datetime is None
        assert entitlement.expired_at is None

        # Verify an entitlement from two years ago is expired and the db row is updated
        past_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=365 * 2)
        entitlement.created = past_datetime
        entitlement.save()
        expired_at_datetime = entitlement.expired_at_datetime
        assert expired_at_datetime
        assert entitlement.expired_at

        # Verify that a brand new entitlement that has been redeemed is not expired
        entitlement = CourseEntitlementFactory.create(enrollment_course_run=self.enrollment)
        assert entitlement.enrollment_course_run
        expired_at_datetime = entitlement.expired_at_datetime
        assert expired_at_datetime is None
        assert entitlement.expired_at is None

        # Verify that an entitlement that has been redeemed but not within 14 days
        # and the course started more than two weeks ago is expired
        past_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=20)
        entitlement.created = past_datetime
        self.enrollment.created = past_datetime
        self.course.start = past_datetime
        entitlement.save()
        self.course.save()
        self.enrollment.save()
        assert entitlement.enrollment_course_run
        expired_at_datetime = entitlement.expired_at_datetime
        assert expired_at_datetime
        assert entitlement.expired_at

        # Verify a date 451 days in the past (1 days after the policy expiration)
        # That is enrolled and started in within the regain period is still expired
        entitlement = CourseEntitlementFactory.create(enrollment_course_run=self.enrollment)
        expired_datetime = datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=451)
        entitlement.created = expired_datetime
        now = datetime.now(tz=pytz.UTC)
        self.enrollment.created = now
        self.course.start = now
        entitlement.save()
        self.course.save()
        self.enrollment.save()
        assert entitlement.enrollment_course_run
        expired_at_datetime = entitlement.expired_at_datetime
        assert expired_at_datetime
        assert entitlement.expired_at
