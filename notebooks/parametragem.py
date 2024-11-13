from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.utils import resample
import pandas as pnd

listas = ['month_2.csv', 'month_3.csv', 'month_4.csv', 'month_5.csv', 'month_6.csv']
df = []
for arquivo in listas:
    df += [pnd.read_csv(arquivo)]
#Concatena todos os dataframes em um único dataframe chamado df
df = pnd.concat(df)
#Chama o dataframe contido na variável chamada df
dadosCadastrais = pnd.read_csv('informacao_cadastral.csv')
usuariosUnicos = dadosCadastrais[dadosCadastrais.situacao == 'CONSUMINDO GÁS']['clientCode'].unique() 
#Organiza os dados dos usuários filtrados pela data
mesFiltrado = df[df['clientCode'].isin(usuariosUnicos)].sort_values(by='datetime') 
#Filtra meterSN diferente de '>N<A'
df = mesFiltrado[mesFiltrado['meterSN'] != '>N<A']
#Garante que todas as linhas com gain nulo sejam preenchidas com 1. Não é garantido que é o valor correto, mas é o melhor que podemos fazer
df['gain'].fillna(1, inplace=True)
#Corrige os pulsos para m²
df['pulseCount'] = df['pulseCount'] * df['gain']
#Cria a variação do pulseCount como uma coluna nova, calculando por grupo a diferença
df['datetime'] = pnd.to_datetime(df['datetime'])
df['dateTimeSegundos'] = df['datetime'].astype(np.int64) // 10**9
df['diffDateTime'] = df.groupby(['clientCode', 'meterSN']).dateTimeSegundos.diff()
df['diffPulseCount'] = df.groupby(['clientCode', 'meterSN']).pulseCount.diff()
df['diffPulseCountTempo'] = df['diffPulseCount'] / df['diffDateTime']
#Preenche os valores nulos (iniciais) com 0
df['diffDateTime'].fillna(0, inplace=True) 
df['diffPulseCount'].fillna(0, inplace=True)
df['diffPulseCountTempo'].fillna(0, inplace=True)
#Reseta o index
df.reset_index(drop=True, inplace=True)
#Seleciona as colunas que serão usadas
df = df[['clientCode', 'meterSN', "pulseCount", 'diffPulseCount','datetime', 'diffDateTime', 'diffPulseCountTempo', 'dateTimeSegundos']]
#Calcula a média e o desvio padrão do diffPulseCount por cliente
df['mediaCliente'] = df.groupby(['clientCode', 'meterSN']).diffPulseCount.transform('mean')
df['desvioPadraoCliente'] = df.groupby(['clientCode', 'meterSN']).diffPulseCount.transform('std')
df['diffDateTime'].describe()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
X_majority = X_test[y_test == 'c']
X_minority = X_test[y_test != 'c']
y_majority = y_test[y_test == 'c']
y_minority = y_test[y_test != 'c']
X_majority_downsampled, y_majority_downsampled = resample(X_majority, y_majority, replace=False, n_samples=len(X_minority), random_state=42)
X_test_balanced = pnd.concat([X_majority_downsampled, X_minority])
y_test_balanced = pnd.concat([y_majority_downsampled, y_minority])
# Definindo o modelo
model = RandomForestClassifier(random_state=42)

# Definindo os hiperparâmetros para o Grid Search
param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}

# Configurando o Grid Search
grid_search = GridSearchCV(estimator=model, param_grid=param_grid, 
                           cv=5, n_jobs=-1, verbose=2, scoring='accuracy')

# Rodando o Grid Search no conjunto de treino
grid_search.fit(X_train, y_train)

# Exibindo os melhores hiperparâmetros
print("Best parameters found: ", grid_search.best_params_)

# Avaliando o modelo no conjunto de teste
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)

# Avaliar a acurácia
from sklearn.metrics import accuracy_score
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy on test data: {accuracy:.2f}")