from mibody.processor import BodyDataRow
from unittest import TestCase
from mibody import BodyData
import subprocess
import datetime
import json
import sys
import io
import os


THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.realpath(os.path.join(THIS_FILE_DIR, '..'))
PYTHON_INTERPRETER = sys.executable


class TestMiBodyProcessing(TestCase):

    """
    Tests the processing of MiBody data only.
    """

    def setUp(self):

        """
        Checks a few things first.
        """

        self.processor_dir = os.path.join(PROJECT_DIR, 'mibody')
        self.assertTrue(
            os.path.isdir(self.processor_dir),
            'Processor directory does not exist')

        self.processor_filename = 'processor.py'
        self.processor_path = os.path.join(
            self.processor_dir, self.processor_filename)
        self.assertTrue(
            os.path.isfile(self.processor_path),
            'Processor file doss not exist')

        self.correct_bodydata_path = '../tests/BODYDATA.TXT'
        self.correct_csv_export_path = '../tests/BODYDATA.CSV'
        self.correct_json_export_path = '../tests/BODYDATA.JSON'

    def _shell_call(self, params=None, *args, **extrakwargs):

        """
        Provides a method to call subprocess.Popen without the additional args.

        :param params: list
        :return: subprocess.Popen instance, stdout, stderr
        """

        if params is None:
            params = []

        params = [PYTHON_INTERPRETER, self.processor_filename] + params

        kwargs = dict(
            cwd=self.processor_dir, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        kwargs.update(extrakwargs)

        process = subprocess.Popen(params, *args, **kwargs)
        return process, process.stdout.read(), process.stderr.read()

    def test_uploading_empty_files(self):

        """
        Tests uploading files, which are incorrectly structured.
        """

        with self.assertRaises(ValueError) as err:
            body_data = BodyData('tests/EMPTY_FILE.TXT')
        self.assertEqual(
            str(err.exception),
            'File, \'tests/EMPTY_FILE.TXT\' has yielded no weigh-ins')

    def test_providing_invalid_file_path(self):

        """
        Tests providing a file path which does not exist or is invalid.
        """

        with self.assertRaises(TypeError) as err:
            BodyData('tests/NON_FILE.TXT')
        self.assertEqual(
            err.exception.args[0], 'File, \'tests/NON_FILE.TXT\' not found')

    def test_processing_test_data(self):

        """
        Tests processing the sample data provided.
        """

        body_data = BodyData('tests/BODYDATA.TXT')

        self.assertEqual(len(body_data), 35)

        for record in body_data:
            self.assertIsInstance(record, BodyDataRow)
            self.assertIsInstance(record.date_time, datetime.datetime)
            self.assertGreater(record.visceral_fat, 0)
            self.assertGreater(record.height, 0)
            self.assertGreater(record.weight, 0)
            self.assertGreater(record.age, 0)
            self.assertEqual(record.gender, 'M')

    def test_command_line_file_path_arguments(self):

        """
        Tests the input file parameter behaviour.
        """

        initial_input_error = b"File, 'BODYDATA.TXT' not found\n"

        # Test default parameters (should read BODYDATA.TXT and print JSON)

        process, _, stderr = self._shell_call()

        # Should have an error as BODYDATA.TXT doesn't exist in same directory

        self.assertEqual(stderr, initial_input_error)

        # Should be fine this time as it's a correct path

        process, _, stderr = self._shell_call([
            '-i', self.correct_bodydata_path])

        self.assertNotEqual(stderr, initial_input_error)

        # If we provide with another invalid path...

        process, _, stderr = self._shell_call([
            '-i', '../tests/NON_BODYDATA.TXT'])

        self.assertEqual(
            stderr, b"File, '../tests/NON_BODYDATA.TXT' not found\n")

        # If we provide an invalid file (empty or malformed)

        for path in ('../tests/DUD_BODYDATA.TXT', '../tests/DUD_BODYDATA.TXT'):

            process, _, stderr = self._shell_call(['-i', path])

            self.assertEqual(
                stderr,
                "File, '{}' has yielded no weigh-ins\n".format(path).encode())

    def test_command_line_export(self):

        """
        Tests exporting data to JSON and CSV via command line utility.
        """

        # TODO: 1. Go through notions of CSV export

        # By default, JSON (test later), provide invalid format

        process, _, stderr = self._shell_call([
            '-i', self.correct_bodydata_path, '-f', 'blah'])
        self.assertEqual(stderr, b"Format, 'blah' is invalid\n")

        # Setting format to CSV should be enough for an output

        process, stdout, _ = self._shell_call([
            '-i', self.correct_bodydata_path, '-f', 'csv'])
        csv_output_1 = stdout

        process, _, _ = self._shell_call([
            '-i', self.correct_bodydata_path, '-f', 'csv',
            '-o', self.correct_csv_export_path])
        csv_file_1 = open('./tests/BODYDATA.CSV', 'r')
        os.unlink('./tests/BODYDATA.CSV')

        self.assertEqual(csv_file_1.read()[:117], str(csv_output_1)[2:119])

        # TODO: 2. Do all CSV-related tests with value differences
        # TODO: 3. Test JSON output and a few more height/weight unit tests

        self.fail('Argument spec and response to be tested')


class MiBodyUnitConversionTestCase(TestCase):

    """
    Tests converting units from processed data.
    """

    def setUp(self):

        self.body_data = BodyData('tests/BODYDATA.TXT')
        self.assertEqual(len(self.body_data), 35)

    def test_converting_weight_units(self):

        """
        Tests converting weight to other units (KG and stones/lbs).
        """

        self.assertEqual(self.body_data[8].weight, 67.9)
        self.assertEqual(self.body_data[8].weight_kg, 67.9)
        self.assertEqual(self.body_data[8].weight_oz, 2395.102016405)
        self.assertEqual(self.body_data[8].weight_lbs, 149.69387602022002)
        self.assertEqual(self.body_data[8].weight_stones, 10.692213)
        self.assertEqual(
            self.body_data[8].weight_lbs_oz,
            (149, 11.102016323520274))
        self.assertEqual(
            self.body_data[8].weight_stones_lbs,
            (10, 9.690982000000009))

        self.assertEqual(self.body_data[18].weight, 65.0)
        self.assertEqual(self.body_data[18].weight_kg, 65.0)
        self.assertEqual(self.body_data[18].weight_oz, 2292.80752675)
        self.assertEqual(self.body_data[18].weight_lbs, 143.300470417)
        self.assertEqual(self.body_data[18].weight_stones, 10.23555)
        self.assertEqual(
            self.body_data[18].weight_lbs_oz,
            (143, 4.807526672000222))
        self.assertEqual(
            self.body_data[18].weight_stones_lbs,
            (10, 3.297699999999999))

        self.assertEqual(self.body_data[34].weight, 66.6)
        self.assertEqual(self.body_data[34].weight_kg, 66.6)
        self.assertEqual(self.body_data[34].weight_oz, 2349.2458658699998)
        self.assertEqual(self.body_data[34].weight_lbs, 146.82786661187998)
        self.assertEqual(self.body_data[34].weight_stones, 10.487502)
        self.assertEqual(
            self.body_data[34].weight_lbs_oz,
            (146, 13.245865790079733))
        self.assertEqual(
            self.body_data[34].weight_stones_lbs,
            (10, 6.825027999999989))

    def test_converting_height_units(self):

        """
        Tests converting height to feet/inches.
        """

        self.assertEqual(self.body_data[34].height, 175)
        self.assertEqual(self.body_data[34].height_cm, 175)
        self.assertEqual(self.body_data[34].height_m, 1.75)
        self.assertEqual(self.body_data[34].height_inches, 68.89763779527559)
        self.assertEqual(self.body_data[34].height_feet, 5.741469816272966)
        self.assertEqual(
            self.body_data[34].height_feet_inches,
            (5, 8.897637795275593))

    def test_calculating_bmr(self):

        """
        Tests calculating the BMR from the given data.
        """

        self.assertEqual(self.body_data[0].age, 21)
        self.assertEqual(self.body_data[0].gender, 'M')
        self.assertEqual(self.body_data[0].height, 175)
        self.assertEqual(self.body_data[0].weight, 66.7)
        self.assertEqual(self.body_data[0].bmr, 1661)

        self.assertEqual(self.body_data[34].age, 21)
        self.assertEqual(self.body_data[34].gender, 'M')
        self.assertEqual(self.body_data[34].height, 175)
        self.assertEqual(self.body_data[34].weight, 66.6)
        self.assertEqual(self.body_data[34].bmr, 1660)

        # Test BMR calculation for female data

        self.body_data[0]['gender'] = 'F'
        self.assertEqual(self.body_data[0].gender, 'F')
        self.assertEqual(self.body_data[0].bmr, 1495)

        self.body_data[34]['gender'] = 'F'
        self.assertEqual(self.body_data[34].gender, 'F')
        self.assertEqual(self.body_data[34].bmr, 1494)

    def test_calculating_bmi(self):

        """
        Tests calculating the BMI from the given data.
        """

        self.assertEqual(self.body_data[0].age, 21)
        self.assertEqual(self.body_data[0].gender, 'M')
        self.assertEqual(self.body_data[0].height, 175)
        self.assertEqual(self.body_data[0].weight, 66.7)
        self.assertEqual(self.body_data[0].bmi, 21.78)

        self.assertEqual(self.body_data[34].age, 21)
        self.assertEqual(self.body_data[34].gender, 'M')
        self.assertEqual(self.body_data[34].height, 175)
        self.assertEqual(self.body_data[34].weight, 66.6)
        self.assertEqual(self.body_data[34].bmi, 21.75)

        # Return classification (overweight etc)

        self.assertEqual(self.body_data[34].classification, 'healthy weight')

        self.body_data[34]['weight'] = 56
        self.assertEqual(self.body_data[34].classification, 'underweight')

        self.body_data[34]['weight'] = 77
        self.assertEqual(self.body_data[34].classification, 'overweight')

        self.body_data[34]['weight'] = 92
        self.assertEqual(self.body_data[34].classification, 'class I obesity')

        self.body_data[34]['weight'] = 108
        self.assertEqual(self.body_data[34].classification, 'class II obesity')

        self.body_data[34]['weight'] = 123
        self.assertEqual(
            self.body_data[34].classification, 'class III obesity')
