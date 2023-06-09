import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout, Conv1D, MaxPooling1D
from tensorflow.keras.optimizers import Adam

# Определим количество дней для прогнозирования
bars_to_predict = 400

# Импорт данных ByBit
with open('data.txt', 'r') as newFile:
    datalist = []
    for item in newFile.read().split('\n'):
        if item:
            datalist.append([float(x) for x in item.split(' ')])

# преобразовать данные в формат DataFrame
df = pd.DataFrame(datalist, columns=['startTime', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'volume', 'turnover'])
df['time'] = pd.to_datetime(df['startTime'], unit='ms')
df.set_index('time', inplace=True)
df.drop(['turnover'], axis=1, inplace=True)
df.columns = ['open', 'startTime', 'high', 'low', 'close', 'volume']
df = df.astype(float)
df = df.iloc[::-1]

# создание новых признаков - скользящие средние и относительная сила индекс
window_size = 60

sma = df['close'].rolling(window_size).mean()
df['SMA'] = sma.fillna(method='bfill')

# создание относительной силы индекса (RSI)
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(window_size).mean()
avg_loss = loss.rolling(window_size).mean().abs()
rs = abs(avg_gain / avg_loss)
rsi = 100 - (100 / (1 + rs))
df['RSI'] = rsi.fillna(method='bfill')

# масштабирование данных
scaler = MinMaxScaler(feature_range=(0, 1))
df['close'] = scaler.fit_transform(np.array(df['close']).reshape(-1, 1))
df['SMA'] = scaler.fit_transform(np.array(df['SMA']).reshape(-1, 1))
df['RSI'] = scaler.fit_transform(np.array(df['RSI']).reshape(-1, 1))

train_size = int(len(df) * 0.99)

model = load_model('model3.h5')
if (model is None):
    # создание сверточной нейронной сети
    # создание модели
    model = Sequential()
    model.add(Conv1D(filters=32, kernel_size=3, activation='relu', input_shape=(window_size, 3)))
    model.add(MaxPooling1D(pool_size=2))
    model.add(Dropout(0.2))
    model.add(Conv1D(filters=64, kernel_size=3, activation='relu'))
    model.add(MaxPooling1D(pool_size=2))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50, return_sequences=True))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50))
    model.add(Dropout(0.2))
    model.add(Dense(units=1))
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')

    # создание обучающей и тестовой выборки
    train_data = df.iloc[:train_size]

    x_train = []
    y_train = []

    for i in range(window_size, len(train_data)):
        x_train.append(train_data[['close', 'SMA', 'RSI']].iloc[i - window_size:i].values)
        y_train.append([train_data['close'].iloc[i]])

    x_train, y_train = np.array(x_train), np.array(y_train)

    # обучение модели
    model.fit(x_train, y_train, epochs=10, batch_size=32)
    # Сохранение модели в файл
    model.save('model3.h5')


# создание новых прогнозов
train_size = len(df) - window_size

predictions = []
for i in range(train_size, train_size + bars_to_predict):
    x_pred = df[['close', 'SMA', 'RSI']].iloc[i - window_size:i].values.reshape(1, window_size, 3)
    prediction = model.predict(x_pred)
    predictions.append(prediction[0][0])
    # добавление новых прогнозов в данные для дальнейшего прогнозирования
    new_row = pd.Series({'close': prediction[0][0]})
    df = pd.concat([df, new_row], ignore_index=True)
    df.at[i, 'SMA'] = df['close'].iloc[i - window_size:i].mean()

    # создание относительной силы индекса (RSI)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window_size).mean()
    avg_loss = loss.rolling(window_size).mean().abs()
    rs = abs(avg_gain / avg_loss)
    rsi = 100 - (100 / (1 + rs))
    df.at[i, 'RSI'] = rsi[i]
    
    # масштабирование новых данных
    df['close'] = scaler.fit_transform(np.array(df['close']).reshape(-1, 1))
    df['SMA'] = scaler.fit_transform(np.array(df['SMA']).reshape(-1, 1))
    df['RSI'] = scaler.fit_transform(np.array(df['RSI']).reshape(-1, 1))

# print(predictions)
# print(df['close'].iloc[-bars_to_predict:].values)
print()
plt.plot(df['close'].iloc[train_size:].values, label='Actual Price')
plt.plot(predictions, label='Predicted Price')
plt.legend()
plt.show()