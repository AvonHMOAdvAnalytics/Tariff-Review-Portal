#import libraries
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import pyodbc
import datetime as dt
from fuzzywuzzy import fuzz, process
import os

#set page configuration and title
st.set_page_config(page_title= 'Provider Review Portal',page_icon='🏥',layout='wide', initial_sidebar_state='expanded')


#assign the image file to a variable and display it
image = Image.open('tariff_portal_image.png')
st.image(image, use_column_width=True)

#write queries to import data from the DB and assign to a varaible as below
query = 'select * from [dbo].[tbl_AvonRevisedProposedStandardTariff]'
query1 = 'select * from [dbo].[tbl_CurrentProviderTariff]'
query2 = 'select Code HospNo,\
        Name ProviderName,\
        ProviderClass,\
        Address,\
        State,\
        City,\
        PhoneNo,\
        Email,\
        ProviderManager\
        from [dbo].[tbl_ProviderList_stg]'
query3 = 'select * from [dbo].[tbl_CPTCodeMaster]'

#a function to connect to the DB server, run the queries above and retrieve the data
@st.cache_data(ttl = dt.timedelta(hours=24))
def get_data_from_sql():
    server = os.environ.get('server_name')
    database = os.environ.get('db_name')
    username = os.environ.get('db_username')
    password = os.environ.get('password')
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER='
        + server
        +';DATABASE='
        + database
        +';UID='
        + username
        +';PWD='
        + password
        )
    # conn = pyodbc.connect(
    #     'DRIVER={ODBC Driver 17 for SQL Server};SERVER='
    #     +st.secrets['server']
    #     +';DATABASE='
    #     +st.secrets['database']
    #     +';UID='
    #     +st.secrets['username']
    #     +';PWD='
    #     +st.secrets['password']
    #     )
    standard_tariff = pd.read_sql(query, conn)
    provider_tariff = pd.read_sql(query1, conn)
    provider_details = pd.read_sql(query2, conn)
    service_details = pd.read_sql(query3,conn)
    conn.close()
    return standard_tariff, provider_tariff, provider_details, service_details

#apply the function above and assign the imported data to variables
standard_tariff, provider_tariff, provider_details, service_details = get_data_from_sql()
#dispay a title on the page
st.title('Provider Tariff Review')
#ensure all the columns below are converted to upper case
service_details['StandardDescription'] = service_details['StandardDescription'].str.upper()
service_details['ServiceType'] = service_details['ServiceType'].str.upper()
service_details['CPTCode'] = service_details['CPTCode'].str.upper()

#store the data in a session state to enable us reference the data from another file
st.session_state['standard_tariff'] = standard_tariff
st.session_state['provider_tariff'] = provider_tariff
st.session_state['provider_details'] = provider_details
st.session_state['service_details'] = service_details

#add a selectbox on the sidebar to enable users select the provider tariff category
tariff_format = st.sidebar.selectbox('Select Provider Tariff Category', options=['Mapped to CPT Codes', 'Not Mapped to CPT Codes'])

#function to compare the service description of the provider with our cpt description and assign a matching score.
def compare_cpt_description(col1,col2):
    return fuzz.ratio(col1, col2)

#function to calculate the percentage difference between levels.
def percent_change(col1, col2):
    return ((col1 - col2)/col2) * 100

#this function filters the entire dataframe based on the selected service category or frequency.
def filter_df(df, selected_category, selected_status):
    filtered_df = df[
        (df['Category'].isin(selected_category)) &
        (df['Frequency'].isin(selected_status))
    ]
    return filtered_df

#this is a function that uses the fuzzy library to compare the provider service description with our standard service description
#and assign a score based on their compatibility and returns the provider description with the highest compatibility score
def fuzzy_match(description, choices):
            best_match, score = process.extractOne(description, choices)
            return best_match, score

#Include an input box that takes in the provider name
provider = st.text_input('Type in Provider Name')
#add a submit button
st.button("Submit", key="button1", help="This is a button")

#include a select box on the sidebar that enables multiple selections to enable users to select multiple service category and frequency
service_cat = st.sidebar.multiselect('Select Service Category', ['DRUGS AND CONSUMABLES', 'CONSULTATIONS', 'INVESTIGATIONS', 'PROCEDURES', 'ROOMS AND FEEDING'])
frequency = st.sidebar.multiselect('Select Service Frequency', [5, 4, 3, 2, 1])

#function to perform the mapping of provider services to AVON standard cpt code.
def map_cptcode_service(serv_cat):
    uploaded_file = st.file_uploader('Upload a CSV file containing Provider Service Description and Tariffs')
    #create a dictionary to map the uploaded file headers to a preferred name according to their index
    preffered_headers = {
        0: 'Description',
        1: 'Amount'
    }
    #set of instructions to be executed if a file is uploaded
    if uploaded_file:
        #read the file and assign to a variable
        df_provider = pd.read_csv(uploaded_file, header=None, skiprows=1)

        #rename the columns based on the preferred_headers disctionary using index
        df_provider.rename(columns=preffered_headers, inplace=True)
        #change to a string data type and convert to upper case
        df_provider['Description'] = df_provider['Description'].astype(str)
        df_provider['Description'] = df_provider['Description'].str.upper()
        #create a variable for only services under CONSULTATION
        selected_services = service_details[service_details['ServiceType'] == serv_cat]
        # Create a dictionary of service descriptions and their corresponding codes
        description_to_code = {
            row['StandardDescription']: row['CPTCode']
            for _, row in selected_services.iterrows()
        }

        # Perform fuzzy matching and map service codes and amounts
        matched_data = []
        for _, row in df_provider.iterrows():
            description = row['Description']
            best_match, score = fuzzy_match(description, description_to_code.keys())
            
            matched_data.append({
                'ProviderDescription': description,
                'CPTCode': description_to_code[best_match],
                'Amount': row['Amount'],
                'FuzzyScore': score,
                'StandardDescription': best_match
            })
        #convert the dictionary above to a pandas dataframe
        matched_df = pd.DataFrame(matched_data)
        #display the data
        st.write(matched_df)
        #add a download button
        st.download_button(
                label=f'Download {provider} tariff data as Excel File',
                data=matched_df.to_csv().encode('utf-8'),
                file_name=f'{provider} tariff data.csv',
                mime='text/csv',
                )

#set of instructions to be executed when 'Mapped to CPT Codes' is selected
if tariff_format == 'Mapped to CPT Codes':
    #create a dictionary to map the uploaded file headers to a preferred name according to their index
    preffered_headers = {
        0: 'CPTCode',
        1: 'Description',
        2: 'Category',
        3: 'ProviderTariff'
    }
    #add an uploader that enable users to upload provider tariff in uploadable format
    uploaded_file = st.file_uploader('Upload the Provider Tariff file already Mapped to CPT Codes here')

    #set of instructions to be executed when a file is uploaded
    if uploaded_file:
    #read the uploaded tariff into a pandas dataframe and assign to tariff
        tariff = pd.read_csv(uploaded_file, header=None, skiprows=1)

        #rename the columns based on the preferred_headers dictionary using index
        tariff.rename(columns=preffered_headers, inplace=True)

        #merge the provider tariff with the AVON standard tariff on CPTCode
        available_df = pd.merge(tariff, standard_tariff, on=['CPTCode'], how='inner', indicator='Exist')
    
        #available_df['Exist'] = np.where(available_df.Exist == 'both', True, False)
        #ensure the dataframe only returns records where the ProviderTariff > 0
        available_df = available_df[available_df['ProviderTariff'] > 0]
        #change the description columns to uppercase
        available_df['Description'] = available_df['Description'].str.upper()
        available_df['CPTDescription'] = available_df['CPTDescription'].str.upper()
        #apply the first fuzzy function that compares the description columns and assign a score based on their compatibility to create a new column
        available_df['Match_Score'] = available_df.apply(lambda row: compare_cpt_description(row['Description'], row['CPTDescription']), axis=1)
        #rename certain columns as below
        available_df.rename(columns={'Description':'ProviderDescription', 'CPTDescription':'StandardDescription','Category_y':'Category'}, inplace=True)
        #return certain columns as selected below
        available = available_df[['CPTCode','Category','ProviderDescription', 'StandardDescription','ProviderTariff','Match_Score']]
        
        #write a condition that compares the tariff provider of each service and the criteria for moving or staying on a particular level
        conditions = [(available_df['ProviderTariff'] < available_df['Level_1']),
                    (available_df['ProviderTariff'] >= available_df['Level_1']) & (available_df['ProviderTariff'] < available_df['Level_2']),
                    (available_df['ProviderTariff'] >= available_df['Level_2']) & (available_df['ProviderTariff'] < available_df['Level_3']),
                    (available_df['ProviderTariff'] >= available_df['Level_3']) & (available_df['ProviderTariff'] < available_df['Level_4']),
                    (available_df['ProviderTariff'] >= available_df['Level_4']) & (available_df['ProviderTariff'] < available_df['Level_5']),
                    (available_df['ProviderTariff'] == available_df['Level_5'])
                    ]
        #assign the corresponding choices based on the conditions above
        choices = ['Below Level 1', 'Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5']
        #apply conditions and choices above to create a new column that contains the Tariff level for each service
        available_df['TariffLevel'] = np.select(conditions, choices, default='Above Level 5')

        #create new columns by applying the percent_change function to get the provider tariff varaince from each standard tariff level
        available_df['Tariff-L1(%)'] = round(percent_change(available_df['ProviderTariff'], available_df['Level_1']),2)
        available_df['Tariff-L2(%)'] = round(percent_change(available_df['ProviderTariff'], available_df['Level_2']),2)
        available_df['Tariff-L3(%)'] = round(percent_change(available_df['ProviderTariff'], available_df['Level_3']),2)
        available_df['Tariff-L4(%)'] = round(percent_change(available_df['ProviderTariff'], available_df['Level_4']),2)
        available_df['Tariff-L5(%)'] = round(percent_change(available_df['ProviderTariff'], available_df['Level_5']),2)

        #create a list with the service categories to be used for recommendation
        cat_for_rec = ['CONSULTATIONS', 'INVESTIGATIONS', 'PROCEDURES', 'ROOMS AND FEEDING']

        #function to calculate the average variance of the provider from the different standard tariff level based on the service frequency
        def calc_ave_var(lev_var, freq):
            ave_for_rec = round(available_df[
                (available_df['Category'].isin(cat_for_rec)) &
                (available_df['Frequency'].isin(freq))
                ][lev_var].mean(),2)
            return ave_for_rec

        #applying the function above to calculate the average tariff variance for high frequency services(5 and 4)
        freq1 = [5,4]  
        ave_for_rec_L1_cond1 = calc_ave_var('Tariff-L1(%)', freq1)
        ave_for_rec_L2_cond1 = calc_ave_var('Tariff-L2(%)', freq1)
        ave_for_rec_L3_cond1 = calc_ave_var('Tariff-L3(%)', freq1)
        ave_for_rec_L4_cond1 = calc_ave_var('Tariff-L4(%)', freq1)
        ave_for_rec_L5_cond1 = calc_ave_var('Tariff-L5(%)', freq1)
        #applying the function above to calculate the average tariff variance for high frequency services 3
        freq2 = [3]
        ave_for_rec_L1_cond2 = calc_ave_var('Tariff-L1(%)', freq2)
        ave_for_rec_L2_cond2 = calc_ave_var('Tariff-L2(%)', freq2)
        ave_for_rec_L3_cond2 = calc_ave_var('Tariff-L3(%)', freq2)
        ave_for_rec_L4_cond2 = calc_ave_var('Tariff-L4(%)', freq2)
        ave_for_rec_L5_cond2 = calc_ave_var('Tariff-L5(%)', freq2)

        #write all the possible recommendations based on the results above and assign each recommendation to a variable
        rec1 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {ave_for_rec_L1_cond1}% and {ave_for_rec_L1_cond2}% from Standard LEVEL 1 Tariff respectively and is hereby recommended to TARIFF LEVEL 1'
        rec2 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {ave_for_rec_L2_cond1}% and {ave_for_rec_L2_cond2}% from Standard LEVEL 2 Tariff respectively and is hereby recommended to TARIFF LEVEL 2'
        rec3 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {ave_for_rec_L3_cond1}% and {ave_for_rec_L3_cond2}% from Standard LEVEL 3 Tariff respectively and is hereby recommended to TARIFF LEVEL 3'
        rec4 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {ave_for_rec_L4_cond1}% and {ave_for_rec_L4_cond2}% from Standard LEVEL 4 Tariff respectively and is hereby recommended to TARIFF LEVEL 4'
        rec5 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {ave_for_rec_L5_cond1}% and {ave_for_rec_L5_cond2}% from Standard LEVEL 5 Tariff respectively and is hereby recommended to TARIFF LEVEL 5'
        rec6 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {ave_for_rec_L5_cond1}% and {ave_for_rec_L5_cond2}% from Standard LEVEL 5 Tariff respectively and is hereby recommended to BUPA LEVEL'
        
        #a function to assign a recommendation to the uploaded provider based on our logic and return the recommendation.
        def check_recommendation():
            if ave_for_rec_L1_cond1 <= 7.5 and ave_for_rec_L1_cond2 <= 15:
                return rec1
            
            if ave_for_rec_L2_cond1 <= 7.5 and ave_for_rec_L2_cond2 <= 15:
                return rec2
            
            if ave_for_rec_L3_cond1 <= 7.5 and ave_for_rec_L3_cond2 <= 15:
                return rec3
            
            if ave_for_rec_L4_cond1 <= 7.5 and ave_for_rec_L4_cond2 <= 15:
                return rec4
            
            if ave_for_rec_L5_cond1 <= 100 and ave_for_rec_L5_cond2 <= 100:
                return rec5
            
            return rec6 

        #a condition to filter the dataframe based on the selected service category and frequency
        if service_cat or frequency:
            filtered_df = filter_df(available_df, service_cat, frequency)

        else:
            filtered_df = available_df

        #another condition to filter the final table to be displayed based on the recommendation of the model for the provider
        #table to be displayed should contain the tariff level of the recommended level and a level below the recommended level
        if check_recommendation() == rec1:
            final_display_df = filtered_df[['CPTCode', 'Category', 'ProviderDescription','StandardDescription','Match_Score', 'Frequency', 'ProviderTariff', 'Level_1', 'Tariff-L1(%)', 'TariffLevel']]
        elif check_recommendation() == rec2:
            final_display_df = filtered_df[['CPTCode', 'Category', 'ProviderDescription','StandardDescription','Match_Score', 'Frequency', 'ProviderTariff', 'Level_1', 'Tariff-L1(%)','Level_2', 'Tariff-L2(%)', 'TariffLevel']]
        elif check_recommendation() == rec3:
            final_display_df = filtered_df[['CPTCode', 'Category', 'ProviderDescription','StandardDescription','Match_Score', 'Frequency', 'ProviderTariff', 'Level_2', 'Tariff-L2(%)', 'Level_3', 'Tariff-L3(%)', 'TariffLevel']]
        elif check_recommendation() == rec4:
            final_display_df = filtered_df[['CPTCode', 'Category', 'ProviderDescription','StandardDescription','Match_Score', 'Frequency', 'ProviderTariff', 'Level_3', 'Tariff-L3(%)', 'Level_4', 'Tariff-L4(%)', 'TariffLevel']]
        elif check_recommendation() == rec5:
            final_display_df = filtered_df[['CPTCode', 'Category', 'ProviderDescription','StandardDescription','Match_Score', 'Frequency', 'ProviderTariff', 'Level_4', 'Tariff-L4(%)', 'Level_5', 'Tariff-L5(%)', 'TariffLevel']]
        elif check_recommendation() == rec6:
            final_display_df = filtered_df[['CPTCode', 'Category', 'ProviderDescription','StandardDescription','Match_Score', 'Frequency', 'ProviderTariff', 'Level_5', 'Tariff-L5(%)', 'TariffLevel']]

        #calculate the average variance of the provider tariff from the standard levels based on the selected service category and frequency
        ave_var_L1 = round(filtered_df['Tariff-L1(%)'].mean(),2)
        ave_var_L2 = round(filtered_df['Tariff-L2(%)'].mean(),2)
        ave_var_L3 = round(filtered_df['Tariff-L3(%)'].mean(),2)
        ave_var_L4 = round(filtered_df['Tariff-L4(%)'].mean(),2)
        ave_var_L5 = round(filtered_df['Tariff-L5(%)'].mean(),2)

        #display a title for the uploaded provider services and classification
        st.title(provider + ' Services Available on AVON STANDARD TARIFF')
        #display only certain columns based on the selected columns below
        display_df = filtered_df[['CPTCode','Category', 'ProviderDescription','StandardDescription','Match_Score','Frequency','ProviderTariff','Level_1','Tariff-L1(%)','Level_2','Tariff-L2(%)', 'Level_3','Tariff-L3(%)', 'Level_4','Tariff-L4(%)', 'Level_5','Tariff-L5(%)', 'TariffLevel']]
        #display the final_display_df 
        st.write(final_display_df)

        #add a download button
        st.download_button(
                label=f'Download {provider} tariff data as Excel File',
                data=final_display_df.to_csv().encode('utf-8'),
                file_name=f'{provider} tariff data.csv',
                mime='text/csv',
                )
        
        #display a title for the displayed variance based on the selections
        st.header('VARIANCE BASED ON SELECTIONS')
        st.write(f'The Average Tariff Variance of {provider} from Standard LEVEL 1 Tariff : {ave_var_L1}%')
        st.write(f'The Average Tariff Variance of {provider} from Standard LEVEL 2 Tariff : {ave_var_L2}%')
        st.write(f'The Average Tariff Variance of {provider} from Standard LEVEL 3 Tariff : {ave_var_L3}%')
        st.write(f'The Average Tariff Variance of {provider} from Standard LEVEL 4 Tariff : {ave_var_L4}%')
        st.write(f'The Average Tariff Variance of {provider} from Standard LEVEL 5 Tariff : {ave_var_L5}%')

        # Check the recommendation using the function
        recommendation = check_recommendation()
        st.header('RECOMMENDATION')
        #use markdown to style the recommendation
        st.markdown(
        f"""
        <style>
        .color-box {{
            background-color: #6E6E70;
            padding: 10px;
            border-radius: 10px;
        }}
        </style>
        <div class='color-box'>{recommendation}</div>""",
        unsafe_allow_html=True,
    )

#set of instructions to be executed when 'Not Mapped to CPT Codes' is selected
elif tariff_format == 'Not Mapped to CPT Codes':
    #add a file uploader        
    serv_cat = st.selectbox('Select Service Category', options=['CONSULTATION', 'SERVICE', 'PROCEDURE', 'SUPPLY', 'ROOM'])
    map_cptcode_service(serv_cat)