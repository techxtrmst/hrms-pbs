from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Q
from companies.models import Company, Location, Holiday, ShiftSchedule
from employees.models import Employee, Attendance
from datetime import date, time, datetime
import pytz

User = get_user_model()


class LocationLogicTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.loc_india = Location.objects.create(
            company=self.company,
            name="India",
            country_code="IN",
            timezone="Asia/Kolkata",
        )
        self.loc_us = Location.objects.create(
            company=self.company,
            name="US",
            country_code="US",
            timezone="America/New_York",
        )

        self.user_india = User.objects.create_user(
            username="india@test.com",
            email="india@test.com",
            password="password",
            company=self.company,
        )
        self.emp_india = Employee.objects.create(
            user=self.user_india,
            company=self.company,
            designation="Developer",
            department="IT",
            location=self.loc_india,
        )

        self.user_us = User.objects.create_user(
            username="us@test.com",
            email="us@test.com",
            password="password",
            company=self.company,
        )
        self.emp_us = Employee.objects.create(
            user=self.user_us,
            company=self.company,
            designation="Manager",
            department="Sales",
            location=self.loc_us,
        )

        self.global_loc = Location.objects.create(
            company=self.company, name="Global", country_code="GL", timezone="UTC"
        )

    def test_holiday_filtering(self):
        # Create a holiday for India
        h_india = Holiday.objects.create(
            company=self.company,
            name="Diwali",
            date=date(2025, 11, 1),
            location=self.loc_india,
        )

        # Create a holiday for Global
        h_global = Holiday.objects.create(
            company=self.company,
            name="New Year",
            date=date(2025, 1, 1),
            location=self.global_loc,
        )

        # Create a holiday for US
        h_us = Holiday.objects.create(
            company=self.company,
            name="Independence Day",
            date=date(2025, 7, 4),
            location=self.loc_us,
        )

        # Verify India employee sees India + Global holidays
        india_holidays = Holiday.objects.filter(company=self.company).filter(
            Q(location=self.emp_india.location) | Q(location__name="Global")
        )
        self.assertEqual(india_holidays.count(), 2)
        self.assertIn(h_india, india_holidays)
        self.assertIn(h_global, india_holidays)
        self.assertNotIn(h_us, india_holidays)

    def test_employee_location_assignment(self):
        self.assertEqual(self.emp_india.location.name, "India")
        self.assertEqual(self.emp_us.location.name, "US")
        self.assertEqual(self.emp_india.location.timezone, "Asia/Kolkata")
        self.assertEqual(self.emp_us.location.timezone, "America/New_York")

    def test_timezone_aware_late_arrival(self):
        # Create a shift for 9:00 AM to 6:00 PM with 15 min grace
        shift = ShiftSchedule.objects.create(
            company=self.company,
            name="General Shift",
            start_time=time(9, 0),
            end_time=time(18, 0),
            grace_period_minutes=15,
        )
        self.emp_india.shift_schedule = shift
        self.emp_india.save()
        self.emp_us.shift_schedule = shift
        self.emp_us.save()

        # Test Case 1: India employee clocks in at 9:10 IST (Not late)
        # Shift start 9:00, Grace 9:15. 9:10 < 9:15.
        # UTC time for 9:10 IST: 9:10 - 5:30 = 3:40 UTC
        tz_india = pytz.timezone("Asia/Kolkata")
        clock_in_india = tz_india.localize(datetime(2025, 10, 1, 9, 10))
        att_india = Attendance.objects.create(
            employee=self.emp_india, date=date(2025, 10, 1), clock_in=clock_in_india
        )
        att_india.calculate_late_arrival()
        self.assertFalse(att_india.is_late)
        self.assertEqual(att_india.late_by_minutes, 0)

        # Test Case 2: India employee clocks in at 9:20 IST (Late by 5 mins after grace)
        # 9:20 - 9:15 = 5 mins
        clock_in_india_late = tz_india.localize(datetime(2025, 10, 1, 9, 20))
        att_india_late = Attendance.objects.create(
            employee=self.emp_india,
            date=date(2025, 10, 2),
            clock_in=clock_in_india_late,
        )
        att_india_late.calculate_late_arrival()
        self.assertTrue(att_india_late.is_late)
        self.assertEqual(att_india_late.late_by_minutes, 5)

        # Test Case 3: US employee clocks in at 9:10 EST (Not late)
        # UTC for 9:10 EST: 9:10 + 5:00 = 14:10 UTC (assuming no DST for simplicity or New York)
        tz_us = pytz.timezone("America/New_York")
        clock_in_us = tz_us.localize(datetime(2025, 10, 1, 9, 10))
        att_us = Attendance.objects.create(
            employee=self.emp_us, date=date(2025, 10, 1), clock_in=clock_in_us
        )
        att_us.calculate_late_arrival()
        self.assertFalse(att_us.is_late)

        # Test Case 4: US employee clocks in at 9:20 EST (Late by 5 mins)
        clock_in_us_late = tz_us.localize(datetime(2025, 10, 1, 9, 20))
        att_us_late = Attendance.objects.create(
            employee=self.emp_us, date=date(2025, 10, 2), clock_in=clock_in_us_late
        )
        att_us_late.calculate_late_arrival()
        self.assertTrue(att_us_late.is_late)
        self.assertEqual(att_us_late.late_by_minutes, 5)
