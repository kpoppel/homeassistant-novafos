import pytest
from . import utils

#@pytest.mark.skip(reason="Skipped")
def test_grouped_statistics_day(mocker, novafos):
    novafos._meter_data = utils.load_data_structure("meter_data_small.json")

    expected = [('2024-01-01', 0.168, 0.168, 0.168, 0.168, 0.168),
                ('2024-01-02', 0.67, 0.502, 0.168, 0.67, 0.419),
                ('2024-01-03', 0.289, -0.381, 0.289, 0.67, 0.48),
                ('2024-01-04', 0.232, -0.057, 0.232, 0.289, 0.261),
                ('2024-01-05', 0.117, -0.115, 0.117, 0.232, 0.175),
                ('2024-01-06', 0.155, 0.038, 0.117, 0.155, 0.136),
                ('2024-01-07', 0.17, 0.015, 0.155, 0.17, 0.163)]

    assert novafos.get_grouped_statistics(meter_type='water', grouping='day') == expected

#@pytest.mark.skip(reason="Skipped")
def test_grouped_statistics_week(data_regression, novafos):
    novafos._meter_data = utils.load_data_structure("meter_data_medium.json")
    expected = [('2024-01-01', 1.801, 0.0, 1.801, 1.801, 1.801),
                ('2024-01-08', 1.96, 0.159, 1.801, 1.96, 1.881),
                ('2024-01-15', 2.032, 0.072, 1.96, 2.032, 1.996),
                ('2024-01-22', 1.98, -0.052, 1.98, 2.032, 2.006),
                ('2024-01-29', 1.979, -0.001, 1.979, 1.98, 1.98),
                ('2024-02-05', 1.808, -0.171, 1.808, 1.979, 1.893),
                ('2024-02-12', 2.296, 0.488, 1.808, 2.296, 2.052),
                ('2024-02-19', 1.833, -0.463, 1.833, 2.296, 2.064),
                ('2024-02-26', 2.412, 0.579, 1.833, 2.412, 2.123),
                ('2024-03-04', 3.529, 1.117, 2.412, 3.529, 2.97),
                ('2024-03-11', 3.103, -0.426, 3.103, 3.529, 3.316), 
                ('2024-03-18', 3.13, 0.027, 3.103, 3.13, 3.117), 
                ('2024-03-25', 3.202, 0.072, 3.13, 3.202, 3.166)]
    assert novafos.get_grouped_statistics(meter_type='water', grouping='week') == expected

#@pytest.mark.skip(reason="Skipped")
def test_grouped_statistics_month(data_regression, novafos):
    novafos._meter_data = utils.load_data_structure("meter_data_large.json")
    expected = [('2024-01-31', 8.604, 0.0, 8.604, 8.604, 8.604),
                ('2024-02-29', 8.336, -0.268, 8.336, 8.604, 8.47),
                ('2024-03-31', 14.125, 5.789, 8.336, 14.125, 11.23),
                ('2024-04-30', 10.416, -3.709, 10.416, 14.125, 12.271),
                ('2024-05-31', 13.62, 3.204, 10.416, 13.62, 12.018),
                ('2024-06-30', 11.472, -2.148, 11.472, 13.62, 12.546),
                ('2024-07-31', 7.59, -3.882, 7.59, 11.472, 9.531), 
                ('2024-08-31', 12.967, 5.377, 7.59, 12.967, 10.279),
                ('2024-09-30', 11.621, -1.346, 11.621, 12.967, 12.294),
                ('2024-10-31', 11.678, 0.057, 11.621, 11.678, 11.649), 
                ('2024-11-30', 14.964, 3.286, 11.678, 14.964, 13.321),
                ('2024-12-31', 13.341, -1.623, 13.341, 14.964, 14.152),
                ('2025-01-01', 2.244, -11.097, 2.244, 13.341, 7.792)]
    assert novafos.get_grouped_statistics(meter_type='water', grouping='month') == expected

#@pytest.mark.skip(reason="Skipped")
def test_grouped_statistics_year(data_regression, novafos):
    novafos._meter_data = utils.load_data_structure("meter_data_large.json")
    expected = [('2024-01-01', 138.734, 0.0, 138.734, 138.734, 138.734),
                ('2025-01-01', 2.244, -136.49, 2.244, 138.734, 70.489)]
    assert novafos.get_grouped_statistics(meter_type='water', grouping='year') == expected
