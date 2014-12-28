# Introducing Python-MiBody!

Behold! Python-MiBody is a lightweight open source Python 3 package for reading
data exported from Salter MiBody scales.

All trademarks remain property of their respective holders, and are used only
to directly describe the products being used.  Their use in no way
indicates any relationship between the author and the holders of said
trademarks.

If any credit has not been given, please raise an issue and this will be looked
in to, and acted upon if required.

## 1. Introduction

The Salter MiBody scales are a great way to keep track of your weight goals,
including muscle mass and body fat. The only letdown, however is the operating
system dependency. This library seeks to provide those using a variety of
operating systems to harness the power of these scales without compromising
their existing operating environments.

## 2. Getting started

While having a dependency on Python to operate, this library sets out to
provide one of two ways to read those BODYDATA.TXT files. The data processor
can be used in the command line to export the data to JSON or CSV format, as
well as the ability to be imported to integrate with existing Python projects.

### 2.1. Installation

You can install this library using pip as usual, using the following command:

``pip install python-mibody``

### 2.2. Command line usage

You can refer to --help for processor.py to understand the command options,
however below are a couple of examples of the command-line behaviour.

#### 2.2.1 Exporting to CSV

The following command will take in the BODYDATA.TXT file and export to CSV
under the file BODYDATA.CSV. In addition, we've stipulated that the height
value in the CSV should be represented in stones and lbs rather than lbs.

``./processor.py -i ./BODYDATA.TXT -o ./BODYDATA.CSV -f csv -w st_lbs``

#### 2.2.2. Export to JSON

Below we've pointed the processor to the same BODYDATA.TXT file, but specified
the format as JSON and added a stipulation to display height in feet and inches
rather than CM.

You may have noticed the -o parameter is missing. You can export the JSON data
to a file using -o, otherwise the output will be printed to the terminal.

``./processor.py -i ./BODYDATA.TXT -f json -h ft_in``

### 2.3. Python library usage

To read the BODYDATA.TXT file, you can either provide the path to the file or
the file itself to the BodyData object as follows.

```python
from mibody import BodyData

processed_data = BodyData('./BODYDATA.TXT')
```

The `processed_data` object can be used similarly to a list, with calls to
`len()` and `processed_data[0]` working as expected. To read records, you can
either iterate over the `processed_data` object or point to a record by index.

Each item in `processed_data` is an instance of `BodyDataRow`, which gives you
some useful functions. See the example below:

```python

In: record = processed_data[0]

In: record
{
    'gender': 'M',
    'body_fat': 14.5,
    'age': 21,
    'visceral_fat': 3,
    'height': 175,
    'fitness_level': 0,
    'date_time': datetime.datetime(2012, 2, 10, 19, 9, 11),
    'weight': 66.7,
    'muscle_mass': 46.6
}

In: record.date_time
datetime.datetime(2012, 2, 10, 19, 9, 11)

In: record.height_feet_inches
(5, 8.897637795275593)

In: record.bmr
1661

In: record.bmi
21.78

In: record.weight
66.7

In: record.weight_stones_lbs
(10, 7.045486000000004)

In: record.classification
'healthy weight'
```

#### 2.3.1. Exporting data to files (as with command-line functionality)

You can export the data to CSV, JSON or io.StringIO from the object as below:

```python

processed_data.export('./BODYDATA.CSV', _format='csv')
```
