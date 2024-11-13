import seaborn as sb
import matplotlib.pyplot as plt
import pandas as pnd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn import svm
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error
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
df['mediaPCTCliente'] = df.groupby(['clientCode', 'meterSN']).diffPulseCountTempo.transform('mean')
df['desvioPadraoPCTCliente'] = df.groupby(['clientCode', 'meterSN']).diffPulseCountTempo.transform('std')
y = df['diffPulseCountTempo']
x = df[['mediaPCTCliente', 'desvioPadraoPCTCliente', 'mediaCliente', 'desvioPadraoCliente', 'dateTimeSegundos']]
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=42)
modelo_ensemble = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=6)
modelo_ensemble.fit(x_train, y_train)
y_pred = modelo_ensemble.predict(x_test)
mse = mean_squared_error(y_test, y_pred)            
df_comparacao = pnd.DataFrame({'Real': y_test,'Previsto': y_pred})
# Exibir as primeiras linhas da tabela comparativa
df_comparacao.describe()
def funcao_objetivo(vetor_refinamento, X_train, y_train, X_test, y_test, model):
    # Ajustar os dados de treinamento e teste com o vetor de refinamento
    X_train_adjusted = X_train * vetor_refinamento
    X_test_adjusted = X_test * vetor_refinamento
    
    # Treinar o modelo com os dados ajustados
    model.fit(X_train_adjusted, y_train)
    
    # Fazer previsões nos dados ajustados
    y_pred = model.predict(X_test_adjusted)
    
    # Calcular o erro quadrático médio
    mse = mean_squared_error(y_test, y_pred)
    
    return mse
def comecarMorcegos(n_bats, n_features):
    # Posições (vetores de refinamento) aleatórias entre [0.8, 1.2]
    positions = np.random.uniform(0.8, 1.2, (n_bats, n_features))
    
    # Velocidades iniciais (vetores aleatórios)
    velocities = np.zeros((n_bats, n_features))
    
    # Frequências
    frequencies = np.zeros(n_bats)
    
    return positions, velocities, frequencies
def bat_algorithm(x_train, y_train, x_test, y_test, model, n_bats, n_iterations, alpha, gamma, freq_min, freq_max, A, r0):
    # Inicializar morcegos
    n_features = x_train.shape[1]  # número de coeficientes no vetor de refinamento
    positions, velocities, frequencies = comecarMorcegos(n_bats, n_features)
    
    # Avaliar fitness inicial
    fitness = np.array([funcao_objetivo(positions[i], x_train, y_train, x_test, y_test, model) for i in range(n_bats)])
    melhor_posicao = positions[np.argmin(fitness)]
    melhor_mse = np.min(fitness)
    
    for t in range(n_iterations):
        for i in range(n_bats):
            # Atualizar frequência
            frequencies[i] = freq_min + (freq_max - freq_min) * np.random.rand()
            
            # Atualizar velocidade
            velocities[i] = velocities[i] + (positions[i] - melhor_posicao) * frequencies[i]
            
            # Atualizar posição
            new_position = positions[i] + velocities[i]
            
            # Gerar uma solução local aleatória se o ruído aleatório for menor que r0
            if np.random.rand() > r0:
                new_position = melhor_posicao + 0.01 * np.random.randn(n_features)
            
            # Limitar os valores da posição entre [0.8, 1.2]
            new_position = np.clip(new_position, 0.8, 1.2)
            
            # Avaliar a nova solução
            new_fitness = funcao_objetivo(new_position, X_train, y_train, X_test, y_test, model)
            
            # Se a nova solução é melhor, aceitar a solução
            if new_fitness < fitness[i] and np.random.rand() < A:
                positions[i] = new_position
                fitness[i] = new_fitness
                
                # Se a nova solução é a melhor até agora, atualizar o melhor
                if new_fitness < melhor_mse:
                    melhor_posicao = new_position
                    melhor_mse = new_fitness
        
        # Atualizar amplitude e taxa de pulso
        A *= alpha
        r0 = r0 * (1 - np.exp(-gamma * t))
        
        print(f'Iteração {t + 1}/{n_iterations}, Melhor fitness: {melhor_mse}')
    
    return melhor_posicao, melhor_mse
melhor_vetor, melhor_mse = bat_algorithm(x_train, y_train, x_test, y_test, modelo_ensemble, n_bats=10, n_iterations=100, alpha=0.9, gamma=0.9, freq_min=0, freq_max=2, A=0.9, r0=0.5)