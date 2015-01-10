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
import json
import csv
import sys
import os
import io


class JSONEncoder(json.JSONEncoder):

    """
    Takes care of JSON-encoding unexpected object types.
    """

    def default(self, obj):

        # Convert date/times to standard __str__ representation
        if isinstance(obj, datetime.datetime):
            return str(obj)

        return json.JSONEncoder.default(self, obj)


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
            except (IOError, OSError):
                raise TypeError(
                    "File, '{}' not found".format(self.file_path_or_object))

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
                self.file_object.close()
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
            self.file_object.close()
            raise ValueError('File, \'{}\' has yielded no weigh-ins'.format(
                self.file_path_or_object))

    def _multi_value_export_format(self, _format, value):

        """
        Returns the correctly-formatted value for the export and type.

        :param _format: str (one of 'json' or 'csv')
        :param value: list
        :return: str or list
        """

        if isinstance(value, tuple):
            if _format == 'csv':
                return '{}, {}'.format(*value)

        return value

    def export(
            self, destination=None, _format='json', height='cm', weight='lbs'):

        """
        Exports the data to a useful format.

        :param destination: str or file-like (The destination or 'stdout')
        :param _format: str (one of 'json' or 'csv')
        :param height: str (one of 'cm' or 'ft_in')
        :param weight: str (one of 'lbs', 'kg' or 'st_lbs')
        """

        assert _format in ('json', 'csv'), \
            "Format must be one of 'cm' or 'ft_in'"

        assert height in ('cm', 'ft_in'), \
            "Height option must be one of 'cm' or 'ft_in'"

        assert weight in ('lbs', 'kg', 'st_lbs'), \
            "Weight option must be one of 'lbs', 'kg' or 'st_lbs'"

        # First step is to format the data accordingly

        height_repr = {
            'cm': 'CM',
            'ft_in': 'feet, inches',
        }

        weight_repr = {
            'lbs': 'lbs',
            'st_lbs': 'stones, lbs',
            'kg': 'KG',
        }

        key_val_map = {
            'gender': 'Gender',
            'age': 'Age (years)',
            'visceral_fat': 'Visceral fat',
            'height': 'Height ({})'.format(height_repr[height]),
            'weight': 'Weight ({})'.format(weight_repr[weight]),
            'date_time': 'Date/time',
            'muscle_mass': 'Muscle mass (%)',
            'body_fat': 'Body fat (%)',
            'fitness_level': 'Fitness level',
            'bmi': 'BMI',
            'bmr': 'BMR',
        }

        final_data = []
        for record in self:

            final_record = record.copy()

            # Set up height and weight values

            final_height = record['height']  # Height already in CM
            if height == 'ft_in':
                final_height = self._multi_value_export_format(
                    _format, record.height_feet_inches)
            final_record.update({'height': final_height})

            final_weight = record['weight']  # Weight already in KG
            if weight == 'lbs':
                final_weight = record.weight_lbs
            if weight == 'st_lbs':
                final_weight = self._multi_value_export_format(
                    _format, record.weight_stones_lbs)
            final_record.update({'weight': final_weight})

            final_record['gender'] = (
                'Male' if final_record['gender'] == 'M' else 'Female')

            # Add the BMI and BMR values to the data

            final_record['bmi'] = record.bmi
            final_record['bmr'] = record.bmr

            final_data.append({
                val: final_record[key] for key, val in key_val_map.items()})

        # Next step is to represent the data as requested

        final_data_str = io.StringIO()
        if _format == 'csv':

            field_names = [
                key_val_map['date_time'],
                key_val_map['gender'],
                key_val_map['age'],
                key_val_map['height'],
                key_val_map['fitness_level'],
                key_val_map['weight'],
                key_val_map['bmi'],
                key_val_map['body_fat'],
                key_val_map['muscle_mass'],
                key_val_map['visceral_fat'],
                key_val_map['bmr'],
            ]

            writer = csv.DictWriter(
                final_data_str, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(final_data)
        elif _format == 'json':
            final_data_str.write(json.dumps(final_data, cls=JSONEncoder))

        # We need to set the file index to 0 before writing the data

        final_data_str.seek(0)

        # Final step is to print final data to stdout or write to file

        if destination is None:
            return final_data_str
        elif destination == 'stdout':
            print(final_data_str.read(), file=sys.stdout)
        elif hasattr(destination, 'seek'):
            for line in final_data_str.readlines():
                destination.write(line)
        else:
            with open(destination, 'w') as f:
                for line in final_data_str.readlines():
                    f.write(line)

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

    def _resolve_path(path, mode=os.R_OK):

        """
        Resolves the provided file to a path.

        :param path: str
        :param mode: os.access mode
        :return: str
        """

        if not os.path.isfile(path):
            path = os.path.join(this_file_dir, path)
            if not os.path.isfile(path):
                path = os.path.expanduser(path)

        path = os.path.realpath(path)

        if mode == os.R_OK and not os.path.isfile(path):
            raise TypeError("File, '{}' not found".format(path))

        if mode:
            if (
                (mode == os.R_OK and not os.access(path, mode)) or
                (mode == os.W_OK and not os.access(
                    os.path.dirname(path), os.W_OK))
            ):
                raise TypeError("File, '{}' is not {}".format(
                    path, ('writeable' if mode == os.W_OK else 'readable')))

        return path

    # Do stuff with arguments

    try:

        source_path = _resolve_path(arguments['--input'])

        processed_body_data = BodyData(source_path)

        if arguments['--format'] not in ('json', 'csv'):
            raise TypeError('Format, \'{}\' is invalid'.format(
                arguments['--format']))

        destination_path = arguments['--output']
        if destination_path != 'stdout':
            destination_path = _resolve_path(destination_path, os.W_OK)

        processed_body_data.export(
            destination_path, arguments['--format'],
            height=arguments['--height'], weight=arguments['--weight'])

    except (TypeError, ValueError, AssertionError) as e:
        print(str(e), file=sys.stderr)
