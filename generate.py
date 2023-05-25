import pandas as pd
import numpy as np
from datetime import date
from joblib import load
import xgboost as xgb
from utils import features, encoding

def generate(X, year, month, day):
    '''
    This function takes raw input, generate features using the raw input and make prediction for the test file.
    '''
    print('Generating sales and promo data for feature engg')
    X.loc[(X.unit_sales<0),'unit_sales'] = 0
    X['unit_sales'] =  X['unit_sales'].apply(lambda x : np.log1p(x))
    X = X.replace(to_replace = [False, True], value = [0, 1])

    sales_data = X.set_index(["store_nbr", "item_nbr", "date"])[["unit_sales"]].unstack(level=-1).fillna(0)
    sales_data.columns = sales_data.columns.get_level_values(1)
    sales_data = sales_data.reset_index()

    train_promo = X.set_index(["store_nbr", "item_nbr", "date"])[["onpromotion"]].unstack(level=-1).fillna(0)
    train_promo.columns = train_promo.columns.get_level_values(1)

    test = pd.read_csv('data/test.csv')
    test = test.replace(to_replace = [False, True], value = [0, 1])

    test_promo = test.set_index(['store_nbr', 'item_nbr', 'date'])[["onpromotion"]].unstack(level=-1).fillna(0)
    test_promo.columns = test_promo.columns.get_level_values(1)
    test_promo = test_promo.reindex(train_promo.index).fillna(0)

    promo_data = pd.concat([train_promo, test_promo], axis=1)
    promo_data = promo_data.reset_index()
    del test, train_promo, test_promo
    print('Data Collected!!!')
    print('Shape of sales and promo data is: {} and {}'.format(sales_data.shape, promo_data.shape))

    print('Generating categorical variables features')
    class_array, family_array, item_array, store_array, store_state_array, store_city_array, store_type_array, store_cluster_array, class_family_df = encoding.generate_cat_features(sales_data)
    print('Categorical variables features generated')

    print('Extracting features for prediction on test data using sales information')
    test_date = date(year, month, day)
    test_dict = features.sales(sales_data, test_date, 'item_store')
    test_item_store_x = pd.DataFrame(test_dict, index = [i for i in range(len(list(test_dict.values())[0]))])

    print('Extracting features for prediction on test data using promo information')
    test_dict = features.promo(promo_data, class_array, family_array, item_array, store_array, store_state_array, store_city_array, store_type_array, store_cluster_array, class_family_df, test_date, 'item_store')
    test_item_store_x1 = pd.DataFrame(test_dict, index = [i for i in range(len(list(test_dict.values())[0]))])
    test_x = test_item_store_x.reset_index(drop = True).merge(test_item_store_x1.reset_index(drop = True), left_index=True, right_index=True)
    [test_x[col].update((test_x[col] - test_x[col].min()) / (test_x[col].max() - test_x[col].min())) for col in test_x.columns]
    print('Shape of test_x is {}'.format(test_x.shape))

    trained_models = []
    for i in range(16):
        model_path = 'models/model_{}.xgb'.format(i)
        xgb_model = xgb.Booster()
        xgb_model.load_model(model_path)
        trained_models.append(xgb_model)

    test_pred = []
    test_dmatrix = xgb.DMatrix(test_x) 
    for model in trained_models:
        test_pred.append(model.predict(test_dmatrix))

    print('Prediction done on test data... generating final output')
    y_test = np.array(test_pred).transpose()

    pred_df = pd.DataFrame(y_test, columns = pd.date_range(str(year) + '-' + str(month) + '-' + str(day), periods = 16))
    pred_df = sales_data[['item_nbr', 'store_nbr']].merge(pred_df, left_index=True, right_index=True)
    pred_df = pred_df.melt(id_vars=['item_nbr', 'store_nbr'], var_name='date', value_name='unit_sales')
    pred_df['unit_sales'] = pred_df['unit_sales'].apply(lambda x : np.expm1(x))
    print('Prediction df generated, loading test file and merging results with test file')
    test_df = pd.read_csv('data/test.csv')
    test_df['date'] = pd.to_datetime(test_df['date'])
    test_df = test_df.merge(pred_df[['item_nbr', 'store_nbr', 'date', 'unit_sales']], on = ['date', 'store_nbr', 'item_nbr'], how = 'left')
    test_df['unit_sales'] = test_df['unit_sales'].clip(lower = 0)
    test_df = test_df.fillna(0)

    return test_df