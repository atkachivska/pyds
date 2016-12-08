# -*- coding: utf-8 -*-

"""
:Authors: Tal Peretz
:Date: 12/8/2016
:TL;DR: this module is responsible for testing cleaning module
"""

import os
import unittest
import pandas as pd
from pyds import cleaning, constants
from tests import data_generators


class PipelineTestCase(unittest.TestCase):
    logger = None
    is_warnings_traced = False

    def setUp(self):
        import traceback
        import warnings
        import sys
        import logging.config

        # setting log configuration
        log_conf_path = os.path.abspath(constants.LOGGER_CONFIGURATION_RELATIVE_PATH)
        logging.config.fileConfig(log_conf_path)
        self.logger = logging.getLogger(__name__)

        def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
            traceback.print_stack()

            log = file if hasattr(file, 'write') else sys.stderr
            log.write(warnings.formatwarning(message, category, filename, lineno, line))

        if self.is_warnings_traced:
            warnings.showwarning = warn_with_traceback

    def test_remove_id_columns(self):
        gen_df = data_generators.generate_random_data(100, 15)
        id_df = data_generators.generate_id_cols(100, 6)
        gen_df_with_id_columns = pd.concat([gen_df, id_df], axis=1)
        gen_df_without_id_cols = cleaning.remove_id_columns(gen_df_with_id_columns)
        self.assertEqual(gen_df.columns, gen_df_without_id_cols.columns)

    def test_fill_missing_values(self):
        # todo: generate dataframes with missing values
        cleaning.fill_missing_values()
        # todo: test received dataframe is filled with reasonable values
        pass

    def test_detect_outliers(self):
        # todo: generate dataframes with outliers
        cleaning.detect_outliers()
        # todo: test received outliers
        pass


if __name__ == '__main__':
    unittest.main()
