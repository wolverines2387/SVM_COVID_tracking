import json
from datetime import date
from urllib.request import urlopen
import time

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
#from pandas.io.json import json_normalize

_ENABLE_PROFILING = False

if _ENABLE_PROFILING:
    import cProfile, pstats, io
    from pstats import SortKey
    pr = cProfile.Profile()
    pr.enable()

today = date.today()

st.set_page_config(
    page_title="Short-term Rental Pricing Predictor",
    layout='wide',
    initial_sidebar_state='auto',
)

sidebar_selection = st.sidebar.radio(
    'Select data:',
    ['columbus','los-angeles', 'new-york-city','fort-worth', 'boston', 'broward-county',
     'chicago', 'austin', 'seattle', 'rochester', 'san-francisco'],
)

@st.cache(ttl=3*60*60, suppress_st_warning=True)
def get_data():
    US_confirmed = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
    US_deaths = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'
    confirmed = pd.read_csv(US_confirmed)
    deaths = pd.read_csv(US_deaths)
    return confirmed, deaths

confirmed, deaths = get_data()
FIPSs = confirmed.groupby(['Province_State', 'Admin2']).FIPS.unique().apply(pd.Series).reset_index()
FIPSs.columns = ['State', 'County', 'FIPS']
FIPSs['FIPS'].fillna(0, inplace = True)
FIPSs['FIPS'] = FIPSs.FIPS.astype(int).astype(str).str.zfill(5)

@st.cache(ttl=3*60*60, suppress_st_warning=True)
def get_testing_data(County):
    apiKey = '9fe19182c5bf4d1bb105da08e593a578'
    if len(County) == 1:
        #print(len(County))
        f = FIPSs[FIPSs.County == County[0]].FIPS.values[0]
        #print(f)
        path1 = 'https://data.covidactnow.org/latest/us/counties/'+f+'.OBSERVED_INTERVENTION.timeseries.json?apiKey='+apiKey
        #print(path1)
        df = json.loads(requests.get(path1).text)
        #print(df.keys())
        data = pd.DataFrame.from_dict(df['actualsTimeseries'])
        data['Date'] = pd.to_datetime(data['date'])
        data = data.set_index('Date')
        #print(data.tail())
        try:
            data['new_negative_tests'] = data['cumulativeNegativeTests'].diff()
            data.loc[(data['new_negative_tests'] < 0)] = np.nan
        except: 
            data['new_negative_tests'] = np.nan
            st.text('Negative test data not avilable')
        data['new_negative_tests_rolling'] = data['new_negative_tests'].fillna(0).rolling(14).mean()


        try:
            data['new_positive_tests'] = data['cumulativePositiveTests'].diff()
            data.loc[(data['new_positive_tests'] < 0)] = np.nan
        except: 
            data['new_positive_tests'] = np.nan
            st.text('test data not avilable')
        data['new_positive_tests_rolling'] = data['new_positive_tests'].fillna(0).rolling(14).mean()
        data['new_tests'] = data['new_negative_tests']+data['new_positive_tests']
        data['new_tests_rolling'] = data['new_tests'].fillna(0).rolling(14).mean()
        data['testing_positivity_rolling'] = (data['new_positive_tests_rolling'] / data['new_tests_rolling'])*100
        #data['testing_positivity_rolling'].tail(14).plot()
        #plt.show()
        return data['new_tests_rolling'], data['testing_positivity_rolling'].iloc[-1:].values[0]
    elif (len(County) > 1) & (len(County) < 5):
        new_positive_tests = []
        new_negative_tests = []
        new_tests = []
        for c in County:
            f = FIPSs[FIPSs.County == c].FIPS.values[0]
            path1 = 'https://data.covidactnow.org/latest/us/counties/'+f+'.OBSERVED_INTERVENTION.timeseries.json?apiKey='+apiKey
            df = json.loads(requests.get(path1).text)
            data = pd.DataFrame.from_dict(df['actualsTimeseries'])
            data['Date'] = pd.to_datetime(data['date'])
            data = data.set_index('Date')
            try:
                data['new_negative_tests'] = data['cumulativeNegativeTests'].diff()
                data.loc[(data['new_negative_tests'] < 0)] = np.nan
            except: 
                data['new_negative_tests'] = np.nan
                #print('Negative test data not avilable')

            try:
                data['new_positive_tests'] = data['cumulativePositiveTests'].diff()
                data.loc[(data['new_positive_tests'] < 0)] = np.nan
            except: 
                data['new_positive_tests'] = np.nan
                #print('Negative test data not avilable')
            data['new_tests'] = data['new_negative_tests']+data['new_positive_tests']

            new_positive_tests.append(data['new_positive_tests'])
            #new_negative_tests.append(data['new_tests'])
            new_tests.append(data['new_tests'])
            #print(data.head())

        new_positive_tests_rolling = pd.concat(new_positive_tests, axis = 1).sum(axis = 1)
        new_positive_tests_rolling = new_positive_tests_rolling.fillna(0).rolling(14).mean()
        #print('new test merging of counties')
        #print(pd.concat(new_tests, axis = 1).head().sum(axis = 1))
        new_tests_rolling = pd.concat(new_tests, axis = 1).sum(axis = 1)
        new_tests_rolling = new_tests_rolling.fillna(0).rolling(14).mean()
        new_tests_rolling = pd.DataFrame(new_tests_rolling).fillna(0)
        new_tests_rolling.columns = ['new_tests_rolling']
        #print('whole df')
        #print(type(new_tests_rolling))
        #print(new_tests_rolling.head())
        #print('single column')
        #print(new_tests_rolling['new_tests_rolling'].head())
        #print('new_positive_tests_rolling')
        #print(new_positive_tests_rolling.head())
        #print('new_tests_rolling')
        #print(new_tests_rolling.head())
        data_to_show = (new_positive_tests_rolling / new_tests_rolling.new_tests_rolling)*100
        #print(data_to_show.shape)
        #print(data_to_show.head())
        #print(data_to_show.columns)
        #print(data_to_show.iloc[-1:].values[0])
        return new_tests_rolling, data_to_show.iloc[-1:].values[0]
    else:
        st.text('Getting testing data for California State')
        path1 = 'https://data.covidactnow.org/latest/us/states/CA.OBSERVED_INTERVENTION.timeseries.json'
        df = json.loads(requests.get(path1).text)
        data = pd.DataFrame.from_dict(df['actualsTimeseries'])
        data['Date'] = pd.to_datetime(data['date'])
        data = data.set_index('Date')

        try:
            data['new_negative_tests'] = data['cumulativeNegativeTests'].diff()
            data.loc[(data['new_negative_tests'] < 0)] = np.nan
        except:
            data['new_negative_tests'] = np.nan
            print('Negative test data not available')
        data['new_negative_tests_rolling'] = data['new_negative_tests'].fillna(0).rolling(14).mean()


        try:
            data['new_positive_tests'] = data['cumulativePositiveTests'].diff()
            data.loc[(data['new_positive_tests'] < 0)] = np.nan
        except:
            data['new_positive_tests'] = np.nan
            st.text('test data not available')
        data['new_positive_tests_rolling'] = data['new_positive_tests'].fillna(0).rolling(14).mean()
        data['new_tests'] = data['new_negative_tests']+data['new_positive_tests']
        data['new_tests_rolling'] = data['new_tests'].fillna(0).rolling(14).mean()
        data['testing_positivity_rolling'] = (data['new_positive_tests_rolling'] / data['new_tests_rolling'])*100
        return data['new_tests_rolling'], data['testing_positivity_rolling'].iloc[-1:].values[0]


def plot_county(county):
    testing_df, testing_percent = get_testing_data(County=county)
    #print(testing_df.head())
    county_confirmed = confirmed[confirmed.Admin2.isin(county)]
    county_confirmed_time = county_confirmed.drop(county_confirmed.iloc[:, 0:12], axis=1).T
    county_confirmed_time = county_confirmed_time.sum(axis= 1)
    county_confirmed_time = county_confirmed_time.reset_index()
    county_confirmed_time.columns = ['date', 'cases']
    county_confirmed_time['Datetime'] = pd.to_datetime(county_confirmed_time['date'])
    county_confirmed_time = county_confirmed_time.set_index('Datetime')
    del county_confirmed_time['date']
    incidence= pd.DataFrame(county_confirmed_time.cases.diff())
    incidence.columns = ['incidence']
    chart_max = incidence.max().values[0]+500

    county_deaths = deaths[deaths.Admin2.isin(county)]
    population = county_deaths.Population.values.sum()

    del county_deaths['Population']
    county_deaths_time = county_deaths.drop(county_deaths.iloc[:, 0:11], axis=1).T
    county_deaths_time = county_deaths_time.sum(axis= 1)

    county_deaths_time = county_deaths_time.reset_index()
    county_deaths_time.columns = ['date', 'deaths']
    county_deaths_time['Datetime'] = pd.to_datetime(county_deaths_time['date'])
    county_deaths_time = county_deaths_time.set_index('Datetime')
    del county_deaths_time['date']

    cases_per100k  = ((county_confirmed_time) * 100000 / population)
    cases_per100k.columns = ['cases per 100K']
    cases_per100k['rolling average'] = cases_per100k['cases per 100K'].rolling(7).mean()

    deaths_per100k  = ((county_deaths_time) * 100000 / population)
    deaths_per100k.columns = ['deaths per 100K']
    deaths_per100k['rolling average'] = deaths_per100k['deaths per 100K'].rolling(7).mean()


    incidence['rolling_incidence'] = incidence.incidence.rolling(7).mean()
    metric = (incidence['rolling_incidence'] * 100000 / population).iloc[[-1]]

    if len(county) == 1:
        st.subheader('Current situation of COVID-19 cases in '+', '.join(map(str, county))+' county ('+ str(today)+')')
    else:
        st.subheader('Current situation of COVID-19 cases in '+', '.join(map(str, county))+' counties ('+ str(today)+')')

    c1 = st.container()
    c2 = st.container()
    c3 = st.container()

    if len(county)==1:
        C = county[0]
        with c2:
            a1, _, a2 = st.columns((3.9, 0.2, 3.9))     
            with a1:
                f = FIPSs[FIPSs.County == C].FIPS.values[0]
                components.iframe("https://covidactnow.org/embed/us/county/"+f, width=350, height=365, scrolling=False)
                
            with a2:
                st.markdown('New cases averaged over last 7 days = %s' %'{:,.1f}'.format(metric.values[0]))
                st.markdown("Population under consideration = %s"% '{:,.0f}'.format(population))
                st.markdown("Total cases = %s"% '{:,.0f}'.format(county_confirmed_time.tail(1).values[0][0]))
                st.markdown("Total deaths = %s"% '{:,.0f}'.format(county_deaths_time.tail(1).values[0][0]))
                st.markdown("% test positivity (14 day average)* = "+"%.2f" % testing_percent)
    elif len(county) <= 3:
        with c2:
            st.write('')
            st.write('')
            st.markdown("New cases averaged over last 7 days = %s" % "{:,.1f}".format(metric.values[0]))
            st.markdown("Population under consideration = %s"% '{:,.0f}'.format(population))
            st.markdown("Total cases = %s"% '{:,.0f}'.format(county_confirmed_time.tail(1).values[0][0]))
            st.markdown("Total deaths = %s"% '{:,.0f}'.format(county_deaths_time.tail(1).values[0][0]))
            st.markdown("% test positivity (14 day average)* = "+"%.2f" % testing_percent)
        with c3:
            columns = st.columns(len(county))
            for idx, C in enumerate(county):
                with columns[idx]:
                    st.write('')
                    st.write('')
                    f = FIPSs[FIPSs.County == C].FIPS.values[0]
                    components.iframe("https://covidactnow.org/embed/us/county/"+f, width=350, height=365, scrolling=False)

    ### Experiment with Altair instead of Matplotlib.
    with c1:
        a2, _, a1 = st.columns((3.9, 0.2, 3.9))

        incidence = incidence.reset_index()
        incidence['nomalized_rolling_incidence'] = incidence['rolling_incidence'] * 100000 / population
        incidence['Phase 2 Threshold'] = 25
        incidence['Phase 3 Threshold'] = 10
        scale = alt.Scale(
            domain=[
                "rolling_incidence",
                "Phase 2 Threshold",
                "Phase 3 Threshold"
            ], range=['#377eb8', '#e41a1c', '#4daf4a'])
        base = alt.Chart(
            incidence,
            title='(A) Weekly rolling mean of incidence per 100K'
        ).transform_calculate(
            base_="'rolling_incidence'",
            phase2_="'Phase 2 Threshold'",
            phase3_="'Phase 3 Threshold'",
        )
        
        ax4 = base.mark_line(strokeWidth=3).encode(
            x=alt.X("Datetime", axis = alt.Axis(title='Date')),
            y=alt.Y("nomalized_rolling_incidence", axis=alt.Axis(title='per 100 thousand')),
            color=alt.Color("base_:N", scale=scale, title="")
        )

        line1 = base.mark_line(strokeDash=[8, 8], strokeWidth=2).encode(
            x=alt.X("Datetime", axis=alt.Axis(title = 'Date')),
            y=alt.Y("Phase 2 Threshold", axis=alt.Axis(title='Count')),
            color=alt.Color("phase2_:N", scale=scale, title="")
        )

        line2 = base.mark_line(strokeDash=[8, 8], strokeWidth=2).encode(
            x=alt.X("Datetime", axis=alt.Axis(title='Date')),
            y=alt.Y("Phase 3 Threshold", axis=alt.Axis(title='Count')),
            color=alt.Color("phase3_:N", scale=scale, title="")
        )

        with a2:
            st.altair_chart(ax4 + line1 + line2, use_container_width=True)

        ax3 = alt.Chart(incidence, title = '(B) Daily incidence (new cases)').mark_bar().encode(
            x=alt.X("Datetime",axis = alt.Axis(title = 'Date')),
            y=alt.Y("incidence",axis = alt.Axis(title = 'Incidence'), scale=alt.Scale(domain=(0, chart_max), clamp=True))
        )
        
        with a1:
            st.altair_chart(ax3, use_container_width=True)
        
        a3, _, a4 = st.columns((3.9, 0.2, 3.9))
        testing_df = pd.DataFrame(testing_df).reset_index()
        #print(testing_df.head())
        #print(type(testing_df))
        
        base = alt.Chart(testing_df, title = '(D) Daily new tests').mark_line(strokeWidth=3).encode(
            x=alt.X("Date",axis = alt.Axis(title = 'Date')),
            y=alt.Y("new_tests_rolling",axis = alt.Axis(title = 'Daily new tests'))
        )
        with a4:
            st.altair_chart(base, use_container_width=True)

        county_confirmed_time = county_confirmed_time.reset_index()
        county_deaths_time = county_deaths_time.reset_index()
        cases_and_deaths = county_confirmed_time.set_index("Datetime").join(county_deaths_time.set_index("Datetime"))
        cases_and_deaths = cases_and_deaths.reset_index()

        # Custom colors for layered charts.
        # See https://stackoverflow.com/questions/61543503/add-legend-to-line-bars-to-altair-chart-without-using-size-color.
        scale = alt.Scale(domain=["cases", "deaths"], range=['#377eb8', '#e41a1c'])
        base = alt.Chart(
            cases_and_deaths,
            title='(C) Cumulative cases and deaths'
        ).transform_calculate(
            cases_="'cases'",
            deaths_="'deaths'",
        )

        c = base.mark_line(strokeWidth=3).encode(
            x=alt.X("Datetime", axis=alt.Axis(title = 'Date')),
            y=alt.Y("cases", axis=alt.Axis(title = 'Count')),
            color=alt.Color("cases_:N", scale=scale, title="")
        )

        d = base.mark_line(strokeWidth=3).encode(
            x=alt.X("Datetime", axis=alt.Axis(title='Date')),
            y=alt.Y("deaths", axis=alt.Axis(title = 'Count')),
            color=alt.Color("deaths_:N", scale=scale, title="")
        )
        with a3:
            st.altair_chart(c+d, use_container_width=True)


def plot_state():
    @st.cache(ttl=3*60*60, suppress_st_warning=True)
    def get_testing_data_state():
            st.text('Getting testing data for California State')
            path1 = 'https://data.covidactnow.org/latest/us/states/CA.OBSERVED_INTERVENTION.timeseries.json'
            df = json.loads(requests.get(path1).text)
            data = pd.DataFrame.from_dict(df['actualsTimeseries'])
            data['Date'] = pd.to_datetime(data['date'])
            data = data.set_index('Date')

            try:
                data['new_negative_tests'] = data['cumulativeNegativeTests'].diff()
                data.loc[(data['new_negative_tests'] < 0)] = np.nan
            except:
                data['new_negative_tests'] = np.nan
                print('Negative test data not available')
            data['new_negative_tests_rolling'] = data['new_negative_tests'].fillna(0).rolling(14).mean()


            try:
                data['new_positive_tests'] = data['cumulativePositiveTests'].diff()
                data.loc[(data['new_positive_tests'] < 0)] = np.nan
            except:
                data['new_positive_tests'] = np.nan
                st.text('test data not available')
            data['new_positive_tests_rolling'] = data['new_positive_tests'].fillna(0).rolling(14).mean()
            data['new_tests'] = data['new_negative_tests']+data['new_positive_tests']
            data['new_tests_rolling'] = data['new_tests'].fillna(0).rolling(14).mean()
            data['testing_positivity_rolling'] = (data['new_positive_tests_rolling'] / data['new_tests_rolling'])*100
            # return data['new_tests_rolling'], data['testing_positivity_rolling'].iloc[-1:].values[0]
            testing_df, testing_percent = data['new_tests_rolling'], data['testing_positivity_rolling'].iloc[-1:].values[0]
            county_confirmed = confirmed[confirmed.Province_State == 'California']
            #county_confirmed = confirmed[confirmed.Admin2 == county]
            county_confirmed_time = county_confirmed.drop(county_confirmed.iloc[:, 0:12], axis=1).T #inplace=True, axis=1
            county_confirmed_time = county_confirmed_time.sum(axis= 1)
            county_confirmed_time = county_confirmed_time.reset_index()
            county_confirmed_time.columns = ['date', 'cases']
            county_confirmed_time['Datetime'] = pd.to_datetime(county_confirmed_time['date'])
            county_confirmed_time = county_confirmed_time.set_index('Datetime')
            del county_confirmed_time['date']
            #print(county_confirmed_time.head())
            incidence = pd.DataFrame(county_confirmed_time.cases.diff())
            incidence.columns = ['incidence']

            #temp_df_time = temp_df.drop(['date'], axis=0).T #inplace=True, axis=1
            county_deaths = deaths[deaths.Province_State == 'California']
            population = county_deaths.Population.values.sum()

            del county_deaths['Population']
            county_deaths_time = county_deaths.drop(county_deaths.iloc[:, 0:11], axis=1).T #inplace=True, axis=1
            county_deaths_time = county_deaths_time.sum(axis= 1)

            county_deaths_time = county_deaths_time.reset_index()
            county_deaths_time.columns = ['date', 'deaths']
            county_deaths_time['Datetime'] = pd.to_datetime(county_deaths_time['date'])
            county_deaths_time = county_deaths_time.set_index('Datetime')
            del county_deaths_time['date']

            cases_per100k  = ((county_confirmed_time)*100000/population)
            cases_per100k.columns = ['cases per 100K']
            cases_per100k['rolling average'] = cases_per100k['cases per 100K'].rolling(7).mean()

            deaths_per100k  = ((county_deaths_time)*100000/population)
            deaths_per100k.columns = ['deaths per 100K']
            deaths_per100k['rolling average'] = deaths_per100k['deaths per 100K'].rolling(7).mean()

            incidence['rolling_incidence'] = incidence.incidence.rolling(7).mean()
            return population, testing_df, testing_percent, county_deaths_time, county_confirmed_time, incidence
    # metric = (incidence['rolling_incidence']*100000/population).iloc[[-1]]

    #print(county_deaths_time.tail(1).values[0])
    #print(cases_per100k.head())
    population, testing_df, testing_percent, county_deaths_time, county_confirmed_time, incidence = get_testing_data_state()
    st.subheader('Current situation of COVID-19 cases in California ('+ str(today)+')')
    c1 = st.container()
    c2 = st.container()
    c3 = st.container()

    with c2:
        a1, _, a2 = st.columns((3.9, 0.2, 3.9))     
        with a1:
            #f = FIPSs[FIPSs.County == C].FIPS.values[0]
            components.iframe("https://covidactnow.org/embed/us/california-ca", width=350, height=365, scrolling=False)

        with a2:
            st.markdown("Population under consideration = %s"% '{:,.0f}'.format(population))
            st.markdown("% test positivity (14 day average) = "+"%.2f" % testing_percent)
            st.markdown("Total cases = %s"% '{:,.0f}'.format(county_confirmed_time.tail(1).values[0][0]))
            st.markdown("Total deaths = %s"% '{:,.0f}'.format(county_deaths_time.tail(1).values[0][0]))
            
    ### Experiment with Altair instead of Matplotlib.
    with c1:
        a2, _, a1 = st.columns((3.9, 0.2, 3.9))

        incidence = incidence.reset_index()
        incidence['nomalized_rolling_incidence'] = incidence['rolling_incidence'] * 100000 / population
        incidence['Phase 2 Threshold'] = 25
        incidence['Phase 3 Threshold'] = 10
        
        scale = alt.Scale(
            domain=[
                "rolling_incidence",
                "Phase 2 Threshold",
                "Phase 3 Threshold"
            ], range=['#377eb8', '#e41a1c', '#4daf4a'])
        base = alt.Chart(
            incidence,
            title='(A) Weekly rolling mean of incidence per 100K'
        ).transform_calculate(
            base_="'rolling_incidence'",
            phase2_="'Phase 2 Threshold'",
            phase3_="'Phase 3 Threshold'",
        )
        
        ax4 = base.mark_line(strokeWidth=3).encode(
            x=alt.X("Datetime", axis = alt.Axis(title='Date')),
            y=alt.Y("nomalized_rolling_incidence", axis=alt.Axis(title='per 100 thousand')),
            color=alt.Color("base_:N", scale=scale, title="")
        )

        line1 = base.mark_line(strokeDash=[8, 8], strokeWidth=2).encode(
            x=alt.X("Datetime", axis=alt.Axis(title = 'Date')),
            y=alt.Y("Phase 2 Threshold", axis=alt.Axis(title='Count')),
            color=alt.Color("phase2_:N", scale=scale, title="")
        )

        line2 = base.mark_line(strokeDash=[8, 8], strokeWidth=2).encode(
            x=alt.X("Datetime", axis=alt.Axis(title='Date')),
            y=alt.Y("Phase 3 Threshold", axis=alt.Axis(title='Count')),
            color=alt.Color("phase3_:N", scale=scale, title="")
        )
        with a2:
            st.altair_chart(ax4 + line1 + line2, use_container_width=True)

        ax3 = alt.Chart(incidence, title = '(B) Daily incidence (new cases)').mark_bar().encode(
            x=alt.X("Datetime",axis = alt.Axis(title = 'Date')),
            y=alt.Y("incidence",axis = alt.Axis(title = 'Incidence'))
        )
        
        with a1:
            st.altair_chart(ax3, use_container_width=True)
        
        a3, _, a4 = st.columns((3.9, 0.2, 3.9))
        testing_df = pd.DataFrame(testing_df).reset_index()
        #print(testing_df.head())
        #print(type(testing_df))
        
        base = alt.Chart(testing_df, title = '(D) Daily new tests').mark_line(strokeWidth=3).encode(
            x=alt.X("Date",axis = alt.Axis(title = 'Date')),
            y=alt.Y("new_tests_rolling",axis = alt.Axis(title = 'Daily new tests'))
        )
        with a4:
            st.altair_chart(base, use_container_width=True)

        county_confirmed_time = county_confirmed_time.reset_index()
        county_deaths_time = county_deaths_time.reset_index()
        cases_and_deaths = county_confirmed_time.set_index("Datetime").join(county_deaths_time.set_index("Datetime"))
        cases_and_deaths = cases_and_deaths.reset_index()

        # Custom colors for layered charts.
        # See https://stackoverflow.com/questions/61543503/add-legend-to-line-bars-to-altair-chart-without-using-size-color.
        scale = alt.Scale(domain=["cases", "deaths"], range=['#377eb8', '#e41a1c'])
        base = alt.Chart(
            cases_and_deaths,
            title='(C) Cumulative cases and deaths'
        ).transform_calculate(
            cases_="'cases'",
            deaths_="'deaths'",
        )

        c = base.mark_line(strokeWidth=3).encode(
            x=alt.X("Datetime", axis=alt.Axis(title = 'Date')),
            y=alt.Y("cases", axis=alt.Axis(title = 'Count')),
            color=alt.Color("cases_:N", scale=scale, title="")
        )

        d = base.mark_line(strokeWidth=3).encode(
            x=alt.X("Datetime", axis=alt.Axis(title='Date')),
            y=alt.Y("deaths", axis=alt.Axis(title = 'Count')),
            color=alt.Color("deaths_:N", scale=scale, title="")
        )
        with a3:
            st.altair_chart(c+d, use_container_width=True)


## functions end here, title, sidebar setting and descriptions start here
t1, t2 = st.columns(2)
with t1:
    st.markdown('Short-term Rental Pricing Predictor')

with t2:
    st.write("")
    st.write("")
    st.write("""
    Prediction data provided by InsideAirbnb | Neighborhood level data provided by Department of Housing and Urban Development
    """)

st.write("")
st.markdown("""
The short-term rental market landscape is quickly changing as inflation in operating expenses, increasing interest rates, and the end of covid stimulus threatens to erode operator profits. At the same time, the proliferation of properties owned solely for short term rental purposes has seen an inflationary impact on housing markets and has threatened renter affordability. Studies such as Horn and Merante's "Is home sharing driving up rents? Evidence from Airbnb in Boston", as well as Barron, Kung, and Proserpio's "The Sharing Economy and Housing Affordability: Evidence from Airbnb", have shown a significant impact of short term rental listings on the neighboring housing market. If this is true, and we believe as other studies such as Scott Susin’s "Rent vouchers and the price of low-income housing", show that the introduction of programs like housing vouchers have a direct impact on housing market affordability, we can logically connect the impact of the affordable housing market to the impact of short-term rentals on the private market.

Our mission is to create a toolset that will allow owner/operators to predict their optimal rental prices, and also visualize their property’s location and provide insight on the impact of listing their property in that neighborhood.


For additional information please contact *ryanwt@umich.edu* or *moura@umich.edu*.  
""")


if sidebar_selection == 'Select Neighborhoods':
    st.markdown('## Select neighborhoods of interest')
    CA_counties = confirmed[confirmed.Province_State == 'California'].Admin2.unique().tolist()
    counties = st.multiselect('', CA_counties, default=['Yolo', 'Solano', 'Sacramento'])
    # Limit to the first 5 counties.
    counties = counties[:5]
    if not counties:
        # If no counties are specified, just plot the state.
        st.markdown('> No counties were selected, falling back to showing statistics for California state.')
        plot_state()
    else:
        # Plot the aggregate and per-county details.
        plot_county(counties)
        for c in counties:
            st.write('')
            with st.expander(f"Expand for {c} County Details"):
                plot_county([c])
elif sidebar_selection == 'California':
    plot_state()

with st.sidebar.expander("Click to learn more about this dashboard"):
    st.markdown(f"""
    One of the key metrics for which data are widely available is the estimate of **daily new cases per 100,000
    population**.

    Here, in following graphics, we will track:

    (A) Estimates of daily new cases per 100,000 population (averaged over the last seven days)  
    
    (B) Daily incidence (new cases)  
    
    (C) Cumulative cases and deaths  
    
    (D) Daily new tests*  

    Data source: Data for cases are procured automatically from **COVID-19 Data Repository by the Center for Systems Science and Engineering (CSSE) at Johns Hopkins University**.  
    
    The data is updated at least once a day or sometimes twice a day in the [COVID-19 Data Repository](https://github.com/CSSEGISandData/COVID-19).  

    Infection rate, positive test rate, ICU headroom and contacts traced from https://covidactnow.org/.  

    *Calculation of % positive tests depends on consistent reporting of county-wise total number of tests performed routinely. Rolling averages and proportions are not calculated if reporting is inconsistent over a period of 14 days.  

    *Report updated on {str(today)}.*  
    """)

if _ENABLE_PROFILING:
    pr.disable()
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    ts = int(time.time())
    with open(f"perf_{ts}.txt", "w") as f:
        f.write(s.getvalue())
