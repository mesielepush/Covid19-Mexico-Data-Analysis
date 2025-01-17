import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import calendar
from datetime import datetime, timedelta

from collections import OrderedDict
from constants import *

plt.style.use('seaborn-whitegrid')

if not os.path.exists('tmp'):
    os.mkdir('tmp')

class Covid:
    
    database = {'confirmed'   : '',
                'suspicious'  : '',
                'negatives'   : '',
                'deaths'      : '',
                'patients'    : ''}

    
    def __init__(self,state):
        if state.lower() in ['national','nacional','all','country']:
            self.state = 'Nacional'
        elif state.lower() in ['cdmx', 'distritofederal', 'df', 'ciudad de mexico']:
            self.state = 'DISTRITO FEDERAL'
        elif state.upper() not in cdns_states:
            print_state_names(state)
            return
        else:
            self.state = state.upper()
        self.state_code = inverse_dict_for_name_states[self.state]

    def __str__(self):
        return f'Data for {self.state},\nstate code: {self.state_code},\npopulation: {self.population()}'

    def discrete(self,data_type):
        data =  pd.read_csv(Covid.database[data_type], encoding='ANSI')
        
        return data.loc[data['nombre'] == self.state].values[0][3:]
    
    def cummulative(self,data_type):
        data =  pd.read_csv(Covid.database[data_type], encoding='ANSI')

        cummulative = []
        raw = data.loc[data['nombre'] == self.state]
        
        for i in raw.values[0][3:]:
            if len(cummulative) == 0:
                cummulative.append(i)
            else:
                cummulative.append(i+cummulative[-1])
        return np.array(cummulative) 
    
    def actives(self,window=14):
        
        try:
            return joblib.load(f'tmp/{self.state}_actives_w_{window}_{Covid.database["patients"][3:6]}.pkl')
        except:
            pass
        if self.state == 'Nacional':
            data = pd.read_csv(Covid.database['patients'], encoding='ANSI')
            data = change_df_names(data)
        else:
            data = pd.read_csv(Covid.database['patients'], encoding='ANSI')
            data = change_df_names(data)
            data = data[data['lives_at'] == self.state_code]
        
        data = data[data['result']==1]
        data['onset_symptoms'] = pd.to_datetime(data['onset_symptoms'])
        
        set_dates = set(data['onset_symptoms'])
        timeline= pd.date_range(start=min(set_dates), end = data['Updated_at'].iloc[0])
        result = {key:0 for key in timeline}
        
        for ind, day_active in enumerate(data['onset_symptoms']):
            for _ in range(window):
                if day_active not in timeline:
                    break
                elif data['day_of_death'].iloc[ind] != '9999-99-99' and day_active > pd.to_datetime(data['day_of_death'].iloc[ind]):
                    break
                else:
                    result[day_active] +=1
                    day_active = day_active + timedelta(days=1)
        
        new_data = pd.DataFrame()
        new_data['actives'] = result.values()
        new_data['dates']   = result.keys()
        new_data = new_data.set_index('dates',drop=True)
        
        joblib.dump(new_data,f'tmp/{self.state}_actives_w_{window}_{Covid.database["patients"][3:6]}.pkl')

        return new_data

    def patients(self):
        return self.Patients(self,change_df_names(pd.read_csv(Covid.database['patients'], encoding='ANSI')))

    def population(self):
        data = pd.read_csv(Covid.database['confirmed'])
        return data[data['nombre']==self.state].poblacion.values[0]

    @staticmethod
    def cohens_d(data1,data2):
        from numpy import mean, var, sqrt
        mean1 = mean(data1)
        mean2 = mean(data2)
        var1  = var(data1)
        var2  = var(data2)
            
        numerator = mean1 - mean2
        
        len1 = len(data1)-1
        len2 = len(data2)-1
        
        total_var = (len1*var1) + (len2*var2)
        total_len = len1 + len2
        
        denominator = sqrt(total_var / total_len)
            
        return numerator / denominator

    @staticmethod
    def plot_actives(data,names,trim=0, title=''):
        plt.close('all')
        plt.rcParams["figure.figsize"] = (15,7)
        
        if type(data) == pd.core.frame.DataFrame:
            new_index = pd.date_range(start=data.index[0], end=data.index[-1])
            
            plt.plot([str(x)[5:11] for x in new_index],data['actives'],label=names)
            plt.scatter(list(range(0,len(data.index)))[-1],data['actives'].iloc[-1])
            plt.text(list(range(0,len(data.index)))[-1],data['actives'].iloc[-1],str(data['actives'].iloc[-1]))
            
        else:
            
            first_day = min([min(x.index) for x in data])
            last_day = max([max(x.index) for x in data])

            new_index = pd.date_range(start=first_day, end=last_day)

            for ind, dataframe in enumerate(data):
                if len(dataframe) != len(new_index):
                    plt.plot([str(x)[5:11] for x in new_index],[0]*(len(new_index)-len(dataframe))+list(dataframe['actives']),label=names[ind])
                    
                else:
                    plt.plot([str(x)[5:11] for x in new_index],dataframe['actives'],label=names[ind])
                plt.scatter(list(range(0,len(new_index)))[-1],dataframe['actives'].iloc[-1])
                plt.text(list(range(0,len(new_index)))[-1],dataframe['actives'].iloc[-1],str(dataframe['actives'].iloc[-1]))

        plt.xticks(rotation=90, fontsize=12)
        plt.xlim(trim,)
        plt.title(title, fontsize=20)
        plt.suptitle(calendar.month_name[int(Covid.database['patients'][2:4])]+'-'+Covid.database['patients'][4:6]+'-20'+Covid.database['patients'][:2], fontsize=18)
        plt.ylabel('Number of Patients', fontsize=16)
        plt.xlabel('Dates', fontsize=16)
        plt.legend(fontsize=14,loc=2)
        plt.show()
    
    @staticmethod
    def plot_cummulative(data, names = None, title = None, trim=None):
        plt.close('all')
        plt.rcParams["figure.figsize"] = (15,7)
        
        today = pd.to_datetime( pd.read_csv(Covid.database['confirmed']).columns[-1],dayfirst=True)
        

        if type(data[0]) == np.int32:
            index = pd.date_range(start= today - timedelta(days=len(data)), end=today, freq='D')
            index = [str(x)[5:10] for x in index]
            plt.plot(index, data, label = names, alpha = 0.6)
            plt.scatter(index[-1],data[-1])
            plt.text(index[-1], data[-1],str(int(data[-1])) , fontsize=14)
        else:
            if len(data) != len(names):
                raise ValueError('Each database should have a name')
            data = [list(x) for x in data]

            max_len = max([len(x) for x in data])-1
            index = pd.date_range(start=today - timedelta(days=max_len), end=today, freq='D')
            index = [str(x)[5:10] for x in index]
            

            for ind,i in enumerate(data):
                if len(i) != max_len:
                    i = [0]*(max_len-len(i)+1)+i

                plt.plot(index,i,label=names[ind])
                plt.scatter(index[-1],i[-1])
                plt.text(index[-1], i[-1],str(int(i[-1])) , fontsize=14)
                

        plt.xticks(rotation=90,fontsize=13)
        plt.title(title, fontsize=18)
        plt.ylabel('Number of Patients', fontsize=16)
        plt.suptitle(calendar.month_name[int(Covid.database['patients'][2:4])]+'-'+Covid.database['patients'][4:6]+'-20'+Covid.database['patients'][:2], fontsize=18)
        plt.xlabel('Dates', fontsize=16)
        if trim:
            plt.xlim(trim,)
            
        plt.legend(loc='upper left',fontsize=14)
        plt.show()

    @staticmethod
    def plot_discrete(data, names = None, title=None, trim=None):
        plt.close('all')
        plt.rcParams["figure.figsize"] = (15,6)
        
        today = pd.to_datetime( pd.read_csv(Covid.database['confirmed']).columns[-1],dayfirst=True)
        
        
        if type(data) == np.ndarray:
            index = pd.date_range(start= (today - timedelta(days=len(data)-1) ), end = today,freq='D')
            index = [str(x)[5:10] for x in index]
            plt.bar(index, data, label = names, alpha = 0.7)
            
        else:

            max_len = max([len(x) for x in data])
            index = pd.date_range(start= (today - timedelta(days=max_len-1) ), end = today,freq='D')
            index = [str(x)[5:10] for x in index]
            
            for ind, i in enumerate(data):
                if len(i) < max_len:
                    i = [0]*(max_len-len(i))+list(i)

                plt.bar(index,i, label = names[ind],alpha = 0.7)

        plt.title(title, fontsize=18)
        plt.legend(loc='upper left',fontsize=14)
        plt.xticks(rotation=90)
        plt.ylabel('Number of Patients', fontsize=16)
        plt.suptitle(calendar.month_name[int(Covid.database['patients'][2:4])]+'-'+Covid.database['patients'][4:6]+'-20'+Covid.database['patients'][:2], fontsize=18)
        plt.xlabel('Dates', fontsize=16)
        if trim:
            plt.xlim(trim,)
        plt.show()

    @staticmethod
    def preprocess():
        from sklearn.model_selection import train_test_split

        deaths = Covid('all').patients().deaths()
        alives = Covid('all').patients().alive()
        data = [alives.data,deaths.data]

        X = []
        for ind, base in enumerate(data):
            base = base[['diabetes', 'copd', 'asthma',
                        'immunosuppression', 'hypertension',
                        'cardiovascular', 'obesity', 'kidney_disease',
                        'smoker','sex','age']]
            base_sex = base['sex'].copy()
            base_age = base['age'].copy()
            base_age_normal = base_age/max(max(data[0]['age']),max(data[1]['age']))
            base_sex.replace(99,2,inplace=True)
            base_sex.replace(1,0,inplace=True)
            base_sex.replace(2,1,inplace=True)

            base = base.replace([97,98,99],2)
            base = base.replace(2,0)
            base['sex']=base_sex
            base['age']=base_age_normal
            base['y'] = [ind]*len(base)
            X.append(base)

        X = pd.concat(X)
        y = X['y']
        X = X.drop('y',axis=1)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

        return X_train, X_test, y_train, y_test

    @classmethod
    def update_data(cls,databases_dir):
        cls.database  = databases_dir

    @classmethod
    def get_max_to_min(cls,dtype, include_national = False, max_to_min = True,window = 14):
                
        if dtype not in ['confirmed','negatives','deaths','suspicious','actives']:
            dtype_error(dtype)
            return
        if include_national:
            names = cdns_states
        else:
            names = [x for x in cdns_states if x != 'Nacional']
        
        if dtype in ['confirmed','negatives','deaths','suspicious']:
            dictionary = {x:sum(cls(x).discrete(dtype)) for x in names}
            return OrderedDict(sorted(dictionary.items(), key=lambda t: t[1],reverse=max_to_min))
        else:
            dictionary = {x:sum(cls(x).actives(window=window).iloc[-1]) for x in names}
            return OrderedDict(sorted(dictionary.items(), key=lambda t: t[1],reverse=max_to_min))

    @classmethod
    def plot_max_to_min(cls,dtype,n=None,title=None, trim=None, include_national = False, max_to_min = True,window=14):
        plt.close('all')
        plt.rcParams["figure.figsize"] = (15,6)
        
        if dtype not in ['confirmed','negatives','deaths','suspicious','actives']:
            dtype_error(dtype)
            return
        if include_national:
            names = cdns_states
        else:
            names = [x for x in cdns_states if x != 'Nacional']
        
        if dtype == 'actives':
            data = {key:Covid(key).actives(window=window) for key in names}
            data = OrderedDict(sorted(data.items(), key=lambda t: t[1].actives.iloc[-1],reverse=max_to_min))
            names = list(data.keys())[:n]

            Covid.plot_actives([data[name] for name in names],names,trim=trim)


        else:
            data = {key:Covid(key).cummulative(dtype) for key in names}
            data = OrderedDict(sorted(data.items(), key=lambda t: t[1][-1],reverse=max_to_min))
            names = list(data.keys())[:n]

            Covid.plot_cummulative([data[name] for name in names],names,trim=trim,title=title)

    @classmethod
    def xgboost_classifier(cls):
        
        from xgboost import XGBClassifier, plot_importance
        from sklearn.metrics import roc_curve, auc, confusion_matrix
        
        print('Starting preprocess of X_train, X_test, y_train, y_test...')
        X_train, X_test, y_train, y_test = cls.preprocess()
        print('#'*15)
        print('Preprocess done...')
        print('#'*15)
        print(f'X_train: {len(X_train)}')
        print(f'X_test: {len(X_test)}')
        print(f'Deaths on train set: {list(y_train.values).count(1)}')
        print(f'Deaths on test set: {list(y_test.values).count(1)}')
        print('#'*15)

        XGBclas_model = XGBClassifier(base_score=0.89,
                                    booster='gbtree', colsample_bylevel=1,
                                    colsample_bynode=1, colsample_bytree=1, gamma=0.1,
                                    learning_rate=0.1, max_delta_step=0, max_depth=10,
                                    min_child_weight=1, missing=None, n_estimators=100, n_jobs=1,
                                    nthread=2, objective='binary:logistic', random_state=0,
                                    reg_alpha=0, reg_lambda=1, scale_pos_weight=1, seed=None,
                                    silent=None, subsample=1, verbosity=1)

        print('#'*15)
        print('Training the model...')
        XGBclas_model.fit(X_train, y_train)
        print('#'*15)
        print('Predicting the Test set: ')
        print('#'*15)
        clas_pred = XGBclas_model.predict(X_test)
        print('Confusion Matrix: ')
        print('[ Alive   Dead]')
        print(confusion_matrix(y_test,clas_pred,labels=[0,1]))

        from sklearn.metrics import roc_curve
        from sklearn.metrics import roc_auc_score

        print('#'*15)
        print('Calculating the ROC curves: ')
        print('#'*15)

        model_probs = XGBclas_model.predict_proba(X_test)
        null_probs = [0 for _ in range(len(y_test))]
        model_positive_probs = model_probs[:, 1]

        null_auc = roc_auc_score(y_test, null_probs)
        model_auc = roc_auc_score(y_test, model_positive_probs)

        print('No Skill: ROC AUC=%.3f' % (null_auc))
        print('Model: ROC AUC=%.3f' % (model_auc))

        null_fpr, null_tpr, _ = roc_curve(y_test, null_probs)
        model_fpr, model_tpr, _ = roc_curve(y_test, model_positive_probs)

        plt.close('all')
        plt.rcParams["figure.figsize"] = (15,6)

        plt.plot(null_fpr, null_tpr, linestyle='--', label='No learning')
        plt.plot(model_fpr, model_tpr, marker='.', label='Model')

        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')

        plt.legend()

        plt.show()

        plt.close('all')
        plot_importance(XGBclas_model)
        plt.show()

        return XGBclas_model

    
    class Patients:
        
        def __init__(self,ob,data):
            self.state = ob.state
            self.state_code = ob.state_code
            if self.state == 'Nacional':
                 self.data = data
            else:
                 self.data = data[data['lives_at'] == self.state_code]
            self.filters = []

        def __str__(self):
            return f'{len(self.data)} Patients data from: {self.state}'

        def age(self,start,end):
            filter = self.data[(self.data.age >=start) & (self.data.age <= end) ]
            if len(filter) == 0:
                raise Exception("This subset of the data is empty, there are no cases with this particularities")

            self.data = filter
            self.filters.append(f'_age_{start}_{end}_')
            return self
        
        def women(self):
            filter = self.data[self.data['sex']==1]
            if len(filter) == 0:
                raise Exception("This subset of the data is empty, there are no cases with this particularities")

            self.data = filter
            self.filters.append('_women_')
            return self
        
        def men(self):
            filter = self.data[self.data['sex']==2]
            if len(filter) == 0:
                raise Exception("This subset of the data is empty, there are no cases with this particularities")
            self.data = filter
            self.filters.append('_men_')
            return self

        def deaths(self):
            filter = self.data[self.data['day_of_death']!='9999-99-99']
            if len(filter) == 0:
                raise Exception("This subset of the data is empty, there are no cases with this particularities")
            self.data = filter
            self.filters.append('_deaths_')
            
            return self
        
        def alive(self):
            filter = self.data[self.data['day_of_death']=='9999-99-99']
            if len(filter) == 0:
                raise Exception("This subset of the data is empty, there are no cases with this particularities")
            self.data = filter
            self.filters.append('_alive_')
            
            return self
        
        def infected(self):
            filter = self.data[self.data['result']==1]
            if len(filter) == 0:
                raise Exception("This subset of the data is empty, there are no cases with this particularities")
            self.data = filter
            self.filters.append('_infected_')
            return self

        def not_infected(self):
            filter = self.data[self.data['result']==2]
            if len(filter) == 0:
                raise Exception("This subset of the data is empty, there are no cases with this particularities")
            self.data = filter
            self.filters.append('_not_infected_')
            
            return self
        
        def actives(self, window = 14):
            
            if len(self.data[self.data['result']==1]) == 0:
                raise Exception("This subset contains no infected")

            try:
                return joblib.load(f'tmp/{self.state}_actives_w_{window}_{[x for x in self.filters]}_{Covid.database["patients"][3:6]}.pkl')
            except:
                pass

            data = self.data[self.data['result']==1].copy()
            data['onset_symptoms'] = pd.to_datetime(data['onset_symptoms'])
            
            set_dates = set(data['onset_symptoms'])
            timeline= pd.date_range(start=min(set_dates), end = data['Updated_at'].iloc[0])
            result = {key:0 for key in timeline}
            
            for ind, day_active in enumerate(data['onset_symptoms']):
                for _ in range(window):
                    if day_active not in timeline:
                        break
                    elif data['day_of_death'].iloc[ind] != '9999-99-99' and day_active > pd.to_datetime(data['day_of_death'].iloc[ind]):
                        break
                    else:
                        result[day_active] +=1
                        day_active = day_active + timedelta(days=1)
            
            new_data = pd.DataFrame()
            new_data['actives'] = result.values()
            new_data['dates']   = result.keys()
            new_data = new_data.set_index('dates',drop=True)
            
            joblib.dump(new_data, f'tmp/{self.state}_actives_w_{window}_{[x for x in self.filters]}_{Covid.database["patients"][3:6]}.pkl')

            return new_data

        def describe(self):
            binary = pd.DataFrame()
            row_name = ['patients']
            row_value = ['--']
            row_n = [len(self.data)]

            if 'result' in self.data.keys():
                row_name.append('covid19+')
                row_value.append( round((list(self.data['result']).count(1) / len(self.data['result'])) *100,2) )
                row_n.append(list(self.data['result']).count(1))

                row_name.append('covid19-')
                row_value.append( round((list(self.data['result']).count(2) / len(self.data['result'])) *100,2) )
                row_n.append(list(self.data['result']).count(2))


                row_name.append('wainting for covid test')
                row_value.append( round((list(self.data['result']).count(3) / len(self.data['result'])) *100,2) )
                row_n.append(list(self.data['result']).count(3))

            if 'sex' in self.data.keys():

                row_name.append('women')
                row_value.append( round((list(self.data['sex']).count(1) / len(self.data['sex'])) *100,2) )
                row_n.append(list(self.data['sex']).count(1))

                row_name.append('men')
                row_value.append( round((list(self.data['sex']).count(2) / len(self.data['sex'])) *100,2) )
                row_n.append(list(self.data['sex']).count(2))

            if 'day_of_death' in self.data.keys():
                row_name.append('deaths') 
                row_value.append(round((len([x for x in self.data['day_of_death'] if x != '9999-99-99'])/len(self.data['day_of_death']))*100,2) )
                row_n.append(len([x for x in self.data['day_of_death'] if x != '9999-99-99']))

            for column in self.data.keys():
                
                if column in ['intubated', 'pneumonia','pregnancy', 'speaks_dialect',
                            'diabetes', 'copd', 'asthma','immunosuppression', 'hypertension',
                            'another_illness','cardiovascular', 'obesity', 'kidney_disease', 'smoker',
                            'close_to_infected','icu']:
                    row_name.append(column)
                    row_value.append( round((list(self.data[column]).count(1) / len(self.data[column])) *100,2) )
                    row_n.append(list(self.data[column]).count(1))

                    
            binary['features'] = row_name
            binary['frequency']  = row_n
            binary['%'] = row_value


            return binary

        def illness(self):
            
            base = self.data[['diabetes', 'copd', 'asthma',
                        'immunosuppression', 'hypertension',
                        'cardiovascular', 'obesity', 'kidney_disease',
                        'smoker','sex','age']]
            base_sex = base['sex'].copy()
            base_age = base['age'].copy()
            base_age_normal = base_age/max(Covid('all').patients().data['age'])
            base_sex.replace(99,2,inplace=True)
            base_sex.replace(1,0,inplace=True)
            base_sex.replace(2,1,inplace=True)

            base = base.replace([97,98,99],2)
            base = base.replace(2,0)
            base['sex']=base_sex
            base['age']=base_age_normal
            
            return base

        def sectors(self):
            plt.close('all')
            plt.rcParams["figure.figsize"] = (15,25)

            sector_bins = {key:list(self.data['sector']).count(key) for key in set(self.data['sector'])}
            ordered = OrderedDict(sorted(sector_bins.items(), key=lambda t: t[1],reverse=True))
            top = list(ordered.keys())[:2]
            others= list(ordered.keys())[2:]


            fig, axs = plt.subplots(3)
            plt.subplots_adjust(left=None, bottom=None, right=None, top=0.8, wspace=0.5, hspace=0.6)

            axs[0].bar([patient_data_keys('sector',x) for x in top],[sector_bins[x] for x in top], alpha=0.5)
            axs[0].text(-.05, sector_bins[top[0]] + (sector_bins[top[0]]*0.06), str(round((sector_bins[top[0]]/len(self.data['sector'])*100),2))+'%', color='black',fontsize=20)
            axs[0].text(.95, sector_bins[top[1]] + (sector_bins[top[1]]*0.06), str(round((sector_bins[top[1]]/len(self.data['sector'])*100),2))+'%', color='black',fontsize=20)
            axs[0].set_title('Sectors with more patients',fontsize=20, pad=30)
            axs[0].set_ylim(0,(max(sector_bins[top[0]],sector_bins[top[1]])+ 1000))
            axs[0].set_ylabel('Number of Patients', fontsize=18)

            axs[1].bar([patient_data_keys('sector',x) for x in others],[sector_bins[x] for x in others],alpha = 0.6)
            axs[1].set_title('Other sectors',fontsize=20, pad=30)
            axs[1].set_ylabel('Number of Patients', fontsize=18)
            
            for ind,sector in enumerate(others):
                axs[1].text(ind-0.3, sector_bins[sector] + (sector_bins[sector]*0.05), str(round((sector_bins[sector]/len(self.data['sector'])*100),2))+'%', color='black',fontsize=16)

            proportions = []
            for sector in ordered.keys():
                sector_total = len(self.data[(self.data.day_of_death != '9999-99-99') & (self.data.sector == sector) ])
                if sector_total == 0:
                    proportions.append(0)
                else:
                    proportions.append(ordered[sector]/sector_total)

            axs[2].bar([patient_data_keys('sector',x) for x in ordered.keys()],proportions,alpha = 0.6, color ='r')
            axs[2].set_title('Death rate for sector', fontsize=23)
            axs[2].set_ylabel('Percentage of Patients', fontsize=18)
            axs[2].set_ylim(0,(max(proportions)+ 10))

            for ind,sector in enumerate(ordered.keys()):
                axs[2].text(ind-0.3, proportions[ind] +1.5, str(round(proportions[ind],2))+'%', color='black',fontsize=14)

            for ax in fig.axes:
                plt.sca(ax)
                plt.xticks(rotation=90,fontsize=16)

            plt.show()
        
        @staticmethod
        def plot_illness():
            plt.close('all')
            plt.rcParams["figure.figsize"] = (15,6)

            alive = Covid('all').patients().alive().illness().drop(['age','sex'],axis=1)
            deaths = Covid('all').patients().deaths().illness().drop(['age','sex'],axis=1)
            plt.bar([x+0.2 for x in range(0,len(alive.keys()))],[(sum(deaths[x])/len(deaths[x]))*100 for x in deaths.keys()], width=0.5,label='deaths',color='r')
            plt.bar(alive.keys(),[(sum(alive[x])/len(alive[x]))*100 for x in alive.keys()], width=0.5,label='alive',color='b')
            plt.legend()
            plt.ylabel('Percentage of population with the affection',fontsize=18)
            plt.suptitle(calendar.month_name[int(Covid.database['patients'][2:4])]+'-'+Covid.database['patients'][4:6]+'-20'+Covid.database['patients'][:2], fontsize=18)
            plt.title('Proportion of Illness in dead vs alive patients',fontsize=20)
            plt.xticks(rotation=75,fontsize=14,fontweight='bold')
            plt.show()

        @staticmethod
        def plot_time_to_death(trim=50):
            plt.close('all')
            plt.rcParams["figure.figsize"] = (15,6)

            data = Covid('all').patients().deaths().infected().data
            result = {}
            for ind, i in enumerate(data['onset_symptoms']):
                time = (pd.to_datetime(data.iloc[ind]['day_of_death']) - pd.to_datetime(i))
                if int(str(time)[:-14]) < 0:
                    continue
                if int(str(time)[:-14]) in result.keys():
                    result[int(str(time)[:-14])]+=1
                else:
                    result[int(str(time)[:-14])]=1    
        
            plt.bar(sorted(result.keys()),[result[x] for x in sorted(result.keys())])
            plt.title('days from onset symptoms to death',fontsize=18)
            plt.ylabel(' number of patients',fontsize=16)
            plt.suptitle(calendar.month_name[int(Covid.database['patients'][2:4])]+'-'+Covid.database['patients'][4:6]+'-20'+Covid.database['patients'][:2], fontsize=18)
            plt.xlabel('Days',fontsize=16)
            plt.xlim(0,trim)