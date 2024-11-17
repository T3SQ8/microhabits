#!/usr/bin/env python3


import datetime
import textwrap
import io
import unittest
import microhabits

class TestStringMethods(unittest.TestCase):

    def test_habits(self):
        habits_file = io.StringIO(textwrap.dedent("""\
        - name: Habit every x days
          frequency: 3
        - name: Habit on certain weekdays
          frequency: ['Monday', 'Wednesday']
        - name: Habit on day of month
          frequency: ['2nd', '15th']
        - name: Habit with no frequency
        - name: Habit with zero frequency
          frequency: 0
        - name: Habit with associated file
          file: ~/file.txt
        """))


        log_file = io.StringIO(textwrap.dedent("""\
        date,name,status
        2024-01-01,Habit every x days,y
        2024-01-04,Habit every x days,s
        2024-01-07,Habit every x days,y
        """))

        habits = microhabits.load_habits_from_file(habits_file)
        habits = microhabits.load_log_from_file(habits, log_file)


        # Testing if frequencies were read properly
        self.assertEqual(habits['Habit every x days'].frequency, 3)
        self.assertEqual(habits['Habit on certain weekdays'].frequency, ['Monday', 'Wednesday'])
        self.assertEqual(habits['Habit on day of month'].frequency, ['2nd', '15th'])
        self.assertEqual(habits['Habit with no frequency'].frequency, 1)
        self.assertEqual(habits['Habit with zero frequency'].frequency, 0)

        # Testing statuses set in log file
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 1)), 'y')
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 4)), 's')
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 5)), None)

        # Testing if setting a status works
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 8)), None)
        habits['Habit every x days'].set_status(datetime.date(2024, 1, 8), 'y')
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 8)), 'y')

        # Testing if toggle_status
        # Should go from None -> 'y' -> 's' -> None -> ...
        habits['Habit every x days'].toggle_status(datetime.date(2024, 1, 27))
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 27)), 'y')
        habits['Habit every x days'].toggle_status(datetime.date(2024, 1, 27))
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 27)), 's')
        habits['Habit every x days'].toggle_status(datetime.date(2024, 1, 27))
        self.assertEqual(habits['Habit every x days'].get_status(datetime.date(2024, 1, 27)), None)




        # Testing is_due for "every x days" habits
        self.assertEqual(habits['Habit every x days'].is_due(datetime.date(2024, 1, 9)),
                         False) # is done the day before so should not be due now
        self.assertEqual(habits['Habit every x days'].is_due(datetime.date(2024, 1, 11)),
                         True) # should be due 3 days later

        # Testing is_due for weekday habits
        self.assertEqual(habits['Habit on certain weekdays'].is_due(datetime.date(2024, 1, 8)),
                         True) # is a monday so should be due
        self.assertEqual(habits['Habit on certain weekdays'].is_due(datetime.date(2024, 1, 12)),
                         False) # is a friday so should not be due

        # Testing is_due for day of month habits
        self.assertEqual(habits['Habit on day of month'].is_due(datetime.date(2024, 1, 15)),
                         True)
        self.assertEqual(habits['Habit on day of month'].is_due(datetime.date(2024, 1, 7)),
                         False)

        # Testing is_due for no frequency
        self.assertEqual(habits['Habit with no frequency'].is_due(datetime.date(2024, 1, 15)),
                         True)

        # Testing is_due for zero frequency
        self.assertEqual(habits['Habit with zero frequency'].is_due(datetime.date(2024, 1, 15)),
                         False)


        # Testing file association
        self.assertEqual(habits['Habit with associated file'].get_file(), '~/file.txt')
        self.assertEqual(habits['Habit with zero frequency'].get_file(), None)



if __name__ == '__main__':
    unittest.main()

