#! /usr/bin/env python

"""Read Salter MiBody scale data

Usage:
  processor.py [-i INFILE] [-o OUTFILE] [-f FORMAT] [-h HEIGHT_UNIT] \
[-w WEIGHT_UNIT]
  processor.py --version
  processor.py --help

Options:
  --version                             Show version.
  --help                                Show this screen.
  -f FORMAT, --format=FORMAT            The format to export to \
[default: json].
  -i INFILE, --input=INFILE             The file to output to \
[default: BODYDATA.TXT].
  -o OUTFILE, --output=OUTFILE          The file to output to \
[default: stdout].
  -h HEIGHT_UNIT, --height=HEIGHT_UNIT  The unit to represent height \
[default: cm].
  -w WEIGHT_UNIT, --weight=WEIGHT_UNIT  The unit to represent weight \
[default: lbs].
"""


import datetime
import docopt
import math
import sys
import os


class BodyDataRow(dict):

    """
    Gives us some funky utilities with each record so we can do conversions
    easily and Pythonically.
    """

    @property
    def weight_kg(self):

        """
        Alias for property, weight.
        """

        return self.weight

    @property
    def weight_oz(self):

        """
        Provides the weight for the record in ounces.
        """

        return self.weight_kg * 35.27396195

    @property
    def weight_lbs(self):

        """
        Provides the weight for the record in lbs.
        """

        return self.weight_kg * 2.2046226218

    @property
    def weight_lbs_oz(self):

        """
        Provides the weight for the record as (lbs, oz).
        """

        whole_lbs = math.floor(self.weight_lbs)
        dec_oz = self.weight_lbs - whole_lbs

        return whole_lbs, dec_oz * 16

    @property
    def weight_stones(self):

        """
        Provides the weight for the record in stones.
        """

        return self.weight_kg * 0.15747

    @property
    def weight_stones_lbs(self):

        """
        Provides the weight for the record in stones.
        """

        whole_stones = math.floor(self.weight_stones)
        dec_lbs = self.weight_stones - whole_stones

        return whole_stones, dec_lbs * 14

    @property
    def height_cm(self):

        """
        Alias for property, height.
        """

        return self.height

    @property
    def height_m(self):

        """
        Provides the height for the record in metres.
        """

        return self.height_cm / 100

    @property
    def height_inches(self):

        """
        Provides the height for the record in inches.
        """

        return self.height_cm / 2.54

    @property
    def height_feet(self):

        """
        Provides the height for the record in feet.
        """

        return self.height_cm / 30.48

    @property
    def height_feet_inches(self):

        """
        Provides the height for the record as (feet, inches).
        """

        whole_feet = math.floor(self.height_feet)
        dec_inches = self.height_feet - whole_feet

        return whole_feet, dec_inches * 12

    @property
    def bmr(self):

        """
        Returns the Basal Metabolic Rate for the record (rounded).

        Calculated using the Mifflin - St Jeor method.
        """

        unmodified_bmr = \
            10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age

        if self.gender == 'M':
            unmodified_bmr += 5
        elif self.gender == 'F':
            unmodified_bmr -= 161
        else:
            unmodified_bmr = 0

        return round(unmodified_bmr)

    @property
    def bmi(self):

        """
        Returns the Body Mass Index for the record (rounded to 2 d.p.).
        """

        return round(self.weight_kg / self.height_m**2, 2)

    @property
    def classification(self):

        """
        Returns the classification for the BMI result. Answers one of:

        underweight, healthy weight, overweight, class I/II/III obesity
        """

        bmi = self.bmi

        if bmi < 18.5:
            return 'underweight'
        elif 18.5 <= bmi < 25:
            return 'healthy weight'
        elif 25 <= bmi < 30:
            return 'overweight'
        elif 30 <= bmi < 35:
            return 'class I obesity'
        elif 35 <= bmi < 40:
            return 'class II obesity'
        elif bmi >= 40:
            return 'class III obesity'
        else:
            return ''

    def __getattribute__(self, item):

        """
        Allow attribute-based key access to data.
        """

        if item in self:
            return self[item]

        return super(BodyDataRow, self).__getattribute__(item)


class BodyData(list):

    """
    Reads the raw data written by Salter MiBody scales and turns it in to
    useful information. Particularly useful to those using an operating system
    other than those supported by the official software provided.
    """

    def __init__(self, file_path_or_object):

        """
        Accepts a path or file object to make use of.

        :param file_path_or_object: str or file
        """

        super(BodyData, self).__init__([])

        self.row_block_size = 18

        self.file_path_or_object = file_path_or_object
        self.final_data = []
        self.file_object = None

        # Check for initial argument data type

        if isinstance(file_path_or_object, str):
            pass
        elif hasattr(file_path_or_object, 'read'):
            self.file_object = file_path_or_object
        else:
            raise TypeError(
                '\'file_path_or_object\' must be valid file path or '
                'file object')

        # If we don't have a file object, we'll want to use the given path

        if not self.file_object:
            try:
                self.file_object = open(self.file_path_or_object, 'rb')
            except FileNotFoundError:
                raise TypeError(
                    'File, \'{}\' not found'.format(self.file_path_or_object))

        self._process()
        self.file_object.close()

    def _process(self):

        """
        Takes care of processing the file data and making some sense of things.
        """

        self.final_data = []

        while True:
            try:
                block = self.file_object.read(self.row_block_size)
            except UnicodeDecodeError:
                raise ValueError(
                    'Read failed, please ensure the file object is opened as '
                    'binary')
            if len(block) != self.row_block_size:
                break

            if block[0]:  # First part of year, seems to be 7 each time

                # Get the date/time

                year = block[0] << 8
                year += block[1]
                month = block[2]
                day = block[3]
                hour = block[4]
                minute = block[5]
                second = block[6]

                weighing_date_time = datetime.datetime(
                    year, month, day, hour, minute, second)

                # Get gender and age

                if block[7] & 128 == 0:
                    gender = 'F'
                else:
                    gender = 'M'
                age = block[7] & ~128

                # Get body measurements

                height = block[8]
                fitness_level = block[9]

                weight_1 = block[10]
                weight_2 = block[11]
                weight = ((weight_1 << 8) + weight_2) / 10

                body_fat_1 = block[12]
                body_fat_2 = block[13]
                body_fat = ((body_fat_1 << 8) + body_fat_2) / 10

                muscle_mass_1 = block[15]
                muscle_mass_2 = block[16]
                muscle_mass = ((muscle_mass_1 << 8) + muscle_mass_2) / 10

                visceral_fat = block[17]

                # Record data

                self.append(BodyDataRow({
                    'date_time': weighing_date_time,
                    'gender': gender,
                    'age': age,
                    'height': height,
                    'fitness_level': fitness_level,
                    'weight': weight,
                    'body_fat': body_fat,
                    'muscle_mass': muscle_mass,
                    'visceral_fat': visceral_fat,
                }))

        if not len(self):
            raise ValueError('File, \'{}\' has yielded no weigh-ins'.format(
                self.file_path_or_object))

    def __str__(self):

        """
        Returns all current data in a nice way.
        """

        if len(self) > 0:
            return '\r\n'.join([str(record) for record in self])

        return 'No weight entries found'

    def __repr__(self):

        """
        Friendly representational string of self.
        """

        return '<BodyData \'{}\'>'.format(self.file_object.name)


if __name__ == '__main__':

    """
    Handle command line arguments should one wish to do it that way.
    """

    this_file_dir = os.path.dirname(os.path.abspath(__file__))
    arguments = docopt.docopt(__doc__, version='0.1')

    # Do stuff with arguments

    source_path = arguments['--input']
    if not os.path.isfile(source_path):
        source_path = os.path.join(this_file_dir, arguments['--input'])
        if not os.path.isfile(source_path):
            source_path = os.path.expanduser(arguments['--input'])

    try:

        processed_body_data = BodyData(source_path)

        if arguments['--format'] == 'json':
            if arguments['--output'] == 'stdout':
                pass  # TODO: Print JSON
            else:
                pass  # TODO: Write JSON to file
        elif arguments['--format'] == 'csv':
            if arguments['--output'] == 'stdout':
                pass  # TODO: This isn't allowed
            else:
                pass  # TODO: Write CSV to file

    except (TypeError, ValueError) as e:
        print(str(e), file=sys.stderr)
