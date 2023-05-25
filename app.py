import pandas as pd
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from train import train
from utils import common
from generate import generate

app = Flask(__name__)
CORS(app)

@app.route('/train', methods=['GET'])
def train_model():
    print('Loading raw data!!!')
    train_df = pd.read_csv('data/train.csv', skiprows=range(1, 101688780))

    print('\nTRAINING HAS BEGUN')
    print('*'*75)
    train(train_df)
    return(jsonify({'Success': 'Training Done'}))

@app.route('/predict', methods=['GET'])
def generate_forcast():
    print('Loading raw data!!!')
    train_df = pd.read_csv('data/train.csv', skiprows=range(1, 101688780))
    
    predictions = generate(train_df, 2017, 8, 16)
    predictions = common.merge(predictions)
    top_categories = common.top_categories(predictions)
    top_stores = common.top_stores(predictions)
    top_items = common.top_items(predictions)

    predictions.to_csv('output/final.csv', index=False)
    top_categories.to_csv('output/categories.csv', index=False)
    top_items.to_csv('output/items.csv', index=False)
    top_stores.to_csv('output/stores.csv', index=False)

    res = {}
    categories_input = top_categories.to_dict(orient='records')
    categories_json = [{'domain': row['family'], 'measure': row['unit_sales']} for row in categories_input]
    res['categories'] = categories_json

    items_input = top_items.to_dict(orient='records')
    items_json = [{'domain': row['item_nbr'], 'measure': row['unit_sales']} for row in items_input]
    res['items'] = items_json

    stores_input = top_stores.to_dict(orient='records')
    stores_json = [{'domain': row['state'], 'measure': row['unit_sales']} for row in stores_input]
    res['stores'] = stores_json

    print(res)
    return(jsonify(res))

@app.route('/quick-predict', methods=['GET'])
def quick_predict():
    res = {}
    categories_input = pd.read_csv('output/categories.csv').to_dict(orient='records')
    categories_json = [{'domain': row['family'], 'measure': row['unit_sales']} for row in categories_input]
    res['categories'] = categories_json

    items_input = pd.read_csv('output/items.csv').to_dict(orient='records')
    items_json = [{'domain': row['item_nbr'], 'measure': row['unit_sales']} for row in items_input]
    res['items'] = items_json

    stores_input = pd.read_csv('output/stores.csv').to_dict(orient='records')
    stores_json = [{'domain': row['state'], 'measure': row['unit_sales']} for row in stores_input]
    res['stores'] = stores_json

    print(res)
    return(jsonify(res))

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)
