import pandas as pd
import pymongo
import json


# Cities Data
#####################################################
# url to scrape for the city population
cities_url ="https://worldpopulationreview.com/world-cities"
# Use panda's `read_html` to parse the url
df_cityPop = pd.read_html(cities_url, header=0)[0]
# rename the columns
df_cityPop.rename(columns={'Name':'City', 
                           '2020 Population':'2020',
                           '2019 Population':'2019'
                          },inplace=True)
# Replace null values with 0
df_cityPop.fillna(0,inplace = True)
#####################################################


# Latest Data
#####################################################
# url to scrape for the Live population data
countries_url ="https://worldpopulationreview.com"
# Use panda's `read_html` to parse the url
df_LatestPop = pd.read_html(countries_url, header=0)[0]
# eliminating unnessasary data
df_LatestPop = df_LatestPop.iloc[:,[1,2,5,6,7,8]]
# rename the columns
df_LatestPop.rename(columns={'2019 Density':'Density_PerSqKm', 
                             'Growth Rate':'Growth_Percentage', 
                             'World %':'World_Percentage'
                            },inplace=True)
                            
# Converting string values to numbers
df_LatestPop['Density_PerSqKm'] = pd.to_numeric(df_LatestPop['Density_PerSqKm'].str.rsplit('/', 0).str.get(0).str.replace(r',', ''))
df_LatestPop['Growth_Percentage'] = pd.to_numeric(df_LatestPop['Growth_Percentage'].str.rsplit('%', 0).str.get(0))
df_LatestPop['World_Percentage'] = pd.to_numeric(df_LatestPop['World_Percentage'].str.rsplit('%', 0).str.get(0))
#####################################################



# Scraping Country codes to merge datasets with
#####################################################
# url to scrape for ISO 3166 country codes Alpha-2 and Alpha-3 from www.iban.com
country_code_url ="https://www.iban.com/country-codes"
# Use panda's `read_html` to parse the url
df_countryCode = pd.read_html(country_code_url, header=0)[0]
# eliminating unnessasary data
df_countryCode = df_countryCode.iloc[:,[1,2]]
# rename the columns
df_countryCode.rename(columns={'Alpha-2 code':'Country_Code',
                               'Alpha-3 code':'Country_Code_3'
                              },inplace=True)
#####################################################


# Countries Population Data
#####################################################
# read Countries population data from csv(source:https://worldpopulationreview.com) into dataframe
df_countries = pd.read_csv('static/data/csvData.csv')
# eliminating unnessasary data
df_countries = df_countries.iloc[:,[0,1,2,3,6,7,8,9]]
# rename the columns
df_countries.rename(columns={'cca2':'Country_Code',
                             'name':'Country',
                             'pop2020':'2020',
                             'pop2019':'2019',
                             'pop2015':'2015',
                             'pop2010':'2010',
                             'pop2000':'2000',
                             'pop1990':'1990' 
                            },inplace=True)

# Removing decimal point from data
# Loop through the columns
for col in df_countries:
    # performing operations on columns other than Country column
    if col not in ["Country_Code", "Country"]:
        df_countries[col] = df_countries[col].astype(str)  # Converting to string

        df_countries[col] = [x.split(".") for x in df_countries[col]]    # Split into 2 strings at the decimal point

        # concatenating both strings choosing only 3 digits from the second string(decimal part)
        df_countries[col] = [ x[0] + x[1][0:3] if len(x[1]) >= 3 \
                         else x[0] + x[1][0:3] + '0' if len(x[1]) == 2 \
                         else x[0] + x[1][0:3] + '00' \
                            for x in df_countries[col]]

        df_countries[col] = df_countries[col].astype(int)     # Converting back to number 




# Another Dataset to merge for additional years data
#####################################################
# Cleaning csv Population data from https://datacatalog.worldbank.org
# reading csv's into dataframes
df_population = pd.read_csv('static/data/population.csv')

# Function to Clean each dataframes
def clean_dataFrames(df, col_list):
    # eliminating unnecessary data
    df = df.iloc[0:217, col_list]
    # renaming columns
    df.rename(columns= {df.columns[0]: "Name"}, inplace = True)
    df = df.rename(columns = lambda x : (str(x)[:-9]))
    df.rename(columns= {df.columns[0]: "Country", df.columns[1]: "Country_Code_3"}, inplace = True)
    return df

# list of required column indexes
col_list = [2,3,11,12,13]
# Calling clean_dataFrames function passing the dataframe as parameter
df_population = clean_dataFrames(df_population, col_list)

# Removing row with no values for the required years(Country Eritrea)
df_population.drop(df_population.index[df_population['Country'] == 'Eritrea'], inplace = True)

# Loop through the columns to covert values from string to 
for col in df_population:
    # performing operations on columns other than Country and Country_Code columns
    if col not in ["Country_Code_3", "Country"]:
        df_population[col] = df_population[col].astype(float)  # Converting string to number




# merging two dataframes for additional years data
#####################################################

# merging df_population with df_countryCode
df_population = df_countryCode.merge(df_population, on="Country_Code_3", how="right")
# removing Country_Code_3 column
del df_population['Country_Code_3']


# merging df_population with df_countries
df_countries = df_countries.merge(df_population, on="Country_Code", how="left")
# removing Country_Code_3 column
del df_countries['Country_y']
# renaming columns
df_population.rename(columns= {"Country_x": "Country"}, inplace = True)
# reordering the columns
df_countries = df_countries.iloc[:,[0,1,2,3,10,9,8,4,5,6,7]]
# Replace null values with 0
df_countries.fillna(0, inplace = True)
#####################################################

#####################################################





# Loading Data into MongoDB
#####################################################
conn = 'mongodb://localhost:27017'
client = pymongo.MongoClient(conn)

db_name = "populationDB"
# # Drop database if exists
if bool(db_name in client.list_database_names()):
    client.drop_database(db_name)

# Creating Database and collection in mongodb
db = client[db_name]
countriesPop = db["countriesPopulation"]
citiesPop = db["citiesPopulation"]
latestPop = db["latestPopulation"]


# Function to insert Dataframes into mongodb collections
def insertToDB(df, collection):
    data_dict = df.to_dict("records") # Convert to dictionary
    # removing index from data
    data_dict = [{k: v for k, v in d.items() if k != 'index'} for d in data_dict]
    collection.insert_one({"data":data_dict}) # Insert dict to collection


# Calling function to insert each dataframes into mongoDB collections
insertToDB(df_countries, countriesPop)
insertToDB(df_cityPop, citiesPop)
insertToDB(df_LatestPop, latestPop)


print(db.list_collection_names())
