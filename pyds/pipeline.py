""" 
:Authors: Tal Peretz
:Date: 10/14/2016
:TL;DR: this module responsible for executing the data science pipelilne and holding it's results
"""
import logging
import time

from pyds import ingestion, exploration, transformations, cleaning, features_engineering, ml

logger = logging.getLogger(__name__)


# Todo: python packaging:
# http://www.aosabook.org/en/packaging.html

# Todo: architecture
# http://www.advogato.org/article/258.html


class PipelineResults:
    """
    this class holds the results for each stage of the data science pipeline
    """

    class Ingestion:
        initial_X_train, initial_X_test, initial_y_train, initial_y_test, numerical_cols, categorical_cols, id_cols = (
            None for _ in range(7))

    class Exploration:
        num_description, cat_description, hist, box_plot, contingency_table, correlations = (
            None for _ in range(6))

    class Cleaning:
        na_rows, imputation, outliers = (None for _ in range(3))

    class Features:
        transformations, created_features = (None for _ in range(2))

    class ML:
        best_model, predictions_df, scores, clusterer_to_results, scatter_plots = (None for _ in range(5))

    def save_ingestion_results(self, X_train, X_test, y_train, y_test, numerical_cols, categorical_cols, id_cols):
        self.Ingestion.initial_X_train = X_train
        self.Ingestion.initial_X_test = X_test
        self.Ingestion.initial_y_train = y_train
        self.Ingestion.initial_y_test = y_test
        self.Ingestion.numerical_cols = numerical_cols
        self.Ingestion.categorical_cols = categorical_cols
        self.Ingestion.id_cols = id_cols

    def save_exploration_results(self, num_description, cat_description, hist, box_plot, contingency_table,
                                 correlations):
        self.Exploration.num_description = num_description
        self.Exploration.cat_description = cat_description
        self.Exploration.hist = hist
        self.Exploration.box_plot = box_plot
        self.Exploration.contingency_table = contingency_table
        self.Exploration.correlations = correlations

    def save_cleaning_results(self, na_rows, imputation, outliers):
        self.Cleaning.na_rows = na_rows
        self.Cleaning.imputation = imputation
        self.Cleaning.outliers = outliers

    def save_features(self, num_transformations, cat_transformations, created_features, selected_features):
        self.Features.num_transformations = num_transformations
        self.Features.cat_transformations = cat_transformations
        self.Features.created_features = created_features
        self.Features.selected_features = selected_features

    def save_models(self, best_model, predictions_df, scores, clusterer_to_results, scatter_plots):
        self.ML.best_model = best_model
        self.ML.predictions_df = predictions_df
        self.ML.scores = scores
        self.ML.clusterer_to_results = clusterer_to_results
        self.ML.scatter_plots = scatter_plots


def exec_pipeline(train_paths, test_paths=None, target_column=None, columns_to_clusterize=None, n_clusters=None):
    """
    given data and arguments describing the data
    this function runs a full pipeline and returns it's result in a PipelineResults object
    :param train_paths: [list of str] full paths for training data
    :param test_paths: [list of str] full paths for test data
    :param target_column: [str] the name of the target variable column
    :param columns_to_clusterize: [list of str] names of columns to cluster the data upon
    :param columns_to_reduce_d: [list of str] names of columns to reduce dimensions upon
    :param n_clusters: [int] number of clusters in data if known
    :param n_components: [int] number of desired dimensions
    :return: pipeline results object holding all results from the process
    """
    pipeline_results = PipelineResults()

    # load data, validate, infer and adjust columns types
    train_df = ingestion.read(train_paths)
    logger.info('loaded train data from %s successfully' % train_paths)
    ingestion.validate_dataset(train_df)
    X_train, X_test, y_train, y_test, is_supervised = ingestion.get_train_test_splits(train_df, test_paths,
                                                                                      target_column)
    logger.info(
        'split data to train and test sets: \nX_train shape - %s \nX_test shape - %s' % (
            X_train.shape, X_test.shape))
    numerical_columns, categorical_columns, id_columns, cols_to_convert_cat = \
        ingestion.infer_columns_statistical_types(X_train, y_train)
    X_train, X_test, y_train, y_test = ingestion.adjust_columns_types(cols_to_convert_cat, X_train, X_test, y_train,
                                                                      y_test)
    logger.info('columns types inferred: \nid - %s \n categorical - %s \n numerical - %s' % (
        id_columns, categorical_columns, numerical_columns))
    pipeline_results.save_ingestion_results(X_train, X_test, y_train, y_test, numerical_columns, categorical_columns,
                                            id_columns)

    # exploration
    num_description, cat_description = exploration.describe(X=X_train, pipeline_results=pipeline_results, y=y_train)
    pipeline_results.save_exploration_results(num_description, cat_description,
                                              exploration.hist(X=X_train, pipeline_results=pipeline_results, y=y_train),
                                              exploration.box_plot(X=X_train, pipeline_results=pipeline_results,
                                                                   y=y_train),
                                              exploration.contingency_table(X=X_train,
                                                                            pipeline_results=pipeline_results,
                                                                            y=y_train),
                                              exploration.correlations(X=X_train, y=y_train))
    logger.info(
        'exploration results are ready: \n numerical columns description - \n%s \n categorical columns description -\n%s'
        % (num_description, cat_description))

    # cleaning
    X_train_without_ids = cleaning.remove_id_columns(X_train, id_columns)
    logger.info('id columns removed')
    filled_X_train, na_rows, imputation = cleaning.fill_missing_values(X_train_without_ids, pipeline_results)
    logger.info('filled %s missing values on train set \n %s' % (len(na_rows.index), imputation.head()))
    outliers = cleaning.detect_outliers(filled_X_train, pipeline_results, y=y_train)
    cleaned_X_train = filled_X_train.drop(outliers, axis=0)
    logger.info('removed %s outliers on train set' % len(outliers))
    ml_ready_y_train = y_train.drop(outliers, axis=0)
    pipeline_results.save_cleaning_results(na_rows, imputation, outliers)

    # features engineering
    transformed_X_train, num_transformations, cat_transformations = \
        transformations.preprocess_train_columns(cleaned_X_train, pipeline_results)
    logger.info('categorical and numerical columns transformed')
    X_train_with_new_features, created_features = features_engineering.create_features(transformed_X_train,
                                                                                       ml_ready_y_train,
                                                                                       pipeline_results)
    logger.info('created new simple features:\n%s' % X_train_with_new_features.columns.tolist())
    ml_ready_X_train, selected_features = features_engineering.select_features(X_train_with_new_features,
                                                                               ml_ready_y_train)
    logger.info('selected features:\n%s' % ml_ready_X_train.columns.tolist())
    pipeline_results.save_features(num_transformations, cat_transformations, created_features, selected_features)

    print(ml_ready_X_train.shape)
    print(ml_ready_X_train.columns.tolist())
    # transform X_test as X_train
    X_test_cols_to_drop = list(set(id_columns).intersection(X_test.columns.tolist()))
    if X_test_cols_to_drop:
        X_test.drop(X_test_cols_to_drop, axis=1, inplace=True)
    filled_X_test = X_test
    if X_test.isnull().values.any():
        filled_X_test = cleaning.fill_missing_values(X_test, pipeline_results)[0]
    transformed_X_test = transformations.transform_test_columns(filled_X_test, pipeline_results)
    X_test_with_new_features, _ = features_engineering.create_features(transformed_X_test,
                                                                       y_test,
                                                                       pipeline_results)
    print(X_test_with_new_features.shape)
    print(X_test_with_new_features.columns.tolist())

    ml_ready_X_test = X_test_with_new_features[
        list(set(selected_features).intersection(X_test_with_new_features.columns.tolist()))]
    print(ml_ready_X_test.shape)
    print(ml_ready_X_test.columns.tolist())
    logger.info('test set transformed successfully\n applying ML models')
    ml_start_time = time.time()
    # ML
    best_model, predictions_df, score, clusterer_to_results = (None for _ in range(4))
    # supervised problem
    if is_supervised:
        # classification problem
        if target_column in pipeline_results.Ingestion.categorical_cols:
            best_model, predictions_df, score = ml.classify(ml_ready_X_train, ml_ready_X_test, ml_ready_y_train,
                                                            y_test)
            logger.info('finished classification')
        # regression problem
        else:
            best_model, predictions_df, score = ml.regress(ml_ready_X_train, ml_ready_X_test, ml_ready_y_train,
                                                           y_test)
            logger.info('finished regression')
    # unsupervised problem
    else:
        clusterer_to_results = ml.create_clusters(ml_ready_X_train, columns_to_clusterize, n_clusters)
        logger.info('finished clustering')
    scatter_plots = exploration.scatter_plot(ml_ready_X_train, ml_ready_y_train)
    logger.info('finished scatter plotting')
    pipeline_results.save_models(best_model, predictions_df, score, clusterer_to_results, scatter_plots)
    logger.info('ml process is finished\n after %s seconds\n best model: \n%s\n score:\n%s\n\n' % (
        (time.time() - ml_start_time), best_model, score))

    return pipeline_results


def low_mem_pipeline(train_paths, test_paths=None, target_column=None, columns_to_clusterize=None,
                     columns_to_reduce_d=None, n_clusters=None, n_components=None):
    pipeline_results = PipelineResults()

    # load data, validate, infer and adjust columns types
    try:
        train_df = ingestion.read_sparse(train_paths)
    except MemoryError:
        # todo:
        pass

    ingestion.validate_dataset(train_df)
    X_train, X_test, y_train, y_test, is_supervised = ingestion.get_train_test_splits(train_paths, test_paths,
                                                                                      target_column)
    numerical_columns, categorical_columns, id_columns, cols_to_convert_cat = \
        ingestion.infer_columns_statistical_types(X_train, y_train)
    X_train, X_test, y_train, y_test = ingestion.adjust_columns_types(cols_to_convert_cat, X_train, X_test, y_train,
                                                                      y_test)
    pipeline_results.save_ingestion_results(X_train, X_test, y_train, y_test, numerical_columns, categorical_columns,
                                            id_columns)

    # exploration
    num_description, cat_description = exploration.describe(X=X_train, pipeline_results=pipeline_results, y=y_train)
    pipeline_results.save_exploration_results(num_description, cat_description,
                                              exploration.hist(X=X_train, pipeline_results=pipeline_results, y=y_train),
                                              exploration.box_plot(X=X_train, pipeline_results=pipeline_results,
                                                                   y=y_train),
                                              exploration.contingency_table(X=X_train,
                                                                            pipeline_results=pipeline_results,
                                                                            y=y_train),
                                              exploration.correlations(X=X_train, y=y_train))

    # cleaning
    X_train_without_ids = cleaning.remove_id_columns(X_train, id_columns)
    filled_X_train, na_rows, imputation = cleaning.fill_missing_values(X_train_without_ids, pipeline_results)
    outliers = cleaning.detect_outliers(filled_X_train, pipeline_results, y=y_train)
    cleaned_X_train = filled_X_train.drop(outliers, axis=0)
    ml_ready_y_train = y_train.drop(outliers, axis=0)
    pipeline_results.save_cleaning_results(na_rows, imputation, outliers)

    # features engineering
    transformed_X_train, num_transformations, cat_transformations = \
        transformations.preprocess_train_columns(cleaned_X_train, pipeline_results)
    X_train_with_new_features, created_features = features_engineering.create_features(transformed_X_train,
                                                                                       ml_ready_y_train,
                                                                                       pipeline_results)
    ml_ready_X_train, selected_features = features_engineering.select_features(X_train_with_new_features,
                                                                               ml_ready_y_train)
    pipeline_results.save_features(num_transformations, cat_transformations, created_features, selected_features)

    # transform X_test as X_train
    X_test_cols_to_drop = set(id_columns).intersection(X_test.columns.tolist())
    if X_test_cols_to_drop:
        X_test.drop(X_test_cols_to_drop, axis=1, inplace=True)
    transformed_X_test = transformations.transform_test_columns(X_test, pipeline_results)
    X_test_with_new_features, _ = features_engineering.create_features(transformed_X_test,
                                                                       y_test,
                                                                       pipeline_results)
    ml_ready_X_test = X_test_with_new_features[selected_features]

    # ML
    best_model, predictions_df, scores, clusterer_to_results = (None for _ in range(4))
    # supervised problem
    if is_supervised:
        # classification problem
        if target_column in pipeline_results.Ingestion.categorical_cols:
            best_model, predictions_df, scores = ml.classify(ml_ready_X_train, ml_ready_X_test, ml_ready_y_train,
                                                             y_test)
        # regression problem
        else:
            best_model, predictions_df, scores = ml.regress(ml_ready_X_train, ml_ready_X_test, ml_ready_y_train,
                                                            y_test)
    # unsupervised problem
    else:
        clusterer_to_results = ml.create_clusters(ml_ready_X_train, columns_to_clusterize, n_clusters)
    scatter_plots = exploration.scatter_plot(ml_ready_X_train, ml_ready_y_train)
    pipeline_results.save_models(best_model, predictions_df, scores, clusterer_to_results, scatter_plots)

    return pipeline_results
