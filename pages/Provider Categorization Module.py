#import needed libraries
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import datetime as dt
from fuzzywuzzy import fuzz

#open the image, assign to a variable and display the variable
image = Image.open('tariff_portal_image.png')
st.image(image, use_column_width=True)

#initialise the dataframe from session_state and assign to a variable to be used in this page
standard_tariff = st.session_state['standard_tariff']
provider_tariff = st.session_state['provider_tariff']
provider_details = st.session_state['provider_details']
service_details = st.session_state['service_details']

#merge the provider_tariff dataframe with provider_details dataframe, rename the cptcode column and select required columns
merged_provider_tariff = pd.merge(provider_tariff, provider_details, on=['HospNo'], how='inner', indicator='Exist')
merged_provider_tariff.rename(columns={'cptcode':'CPTCode'}, inplace=True)
merged_provider_tariff = merged_provider_tariff[['CPTCode', 'CPTDescription', 'Amount', 'ProviderName', 'ProviderClass', 'State']]
# merged_provider_tariff['HospNo'] = merged_provider_tariff['HospNo'].astype(str)

#function to calculate the percentage difference between levels.
def percent_change(col1, col2):
    return ((col1 - col2)/col2) * 100

#function to compare the service description of the provider with our cpt description and assign a matching score.
def compare_cpt_description(col1,col2):
    return fuzz.ratio(col1, col2)

#columns to merge from the merged_provider_tariff
cols_to_merge1 = ['CPTCode', 'CPTDescription', 'Amount', 'ProviderName', 'ProviderClass', 'State']
#columns to merge from the AVON standard tariff dataframe
cols_to_merge = ['CPTCode','CPTDescription','Category', 'Frequency', 'Level_1', 'Level_2', 'Level_3', 'Level_4', 'Level_5']

# Merge standard_tariff outside the loop
merged_provider_standard_tariff = pd.merge(merged_provider_tariff[cols_to_merge1], standard_tariff[cols_to_merge], on=['CPTCode'], how='inner', indicator='Exist')



# Calculate %Variance of each service tariff from the 5 different levels and add as columns to the df
merged_provider_standard_tariff['Tariff-L1%'] = round(percent_change(merged_provider_standard_tariff['Amount'], merged_provider_standard_tariff['Level_1']), 2)
merged_provider_standard_tariff['Tariff-L2%'] = round(percent_change(merged_provider_standard_tariff['Amount'], merged_provider_standard_tariff['Level_2']), 2)
merged_provider_standard_tariff['Tariff-L3%'] = round(percent_change(merged_provider_standard_tariff['Amount'], merged_provider_standard_tariff['Level_3']), 2)
merged_provider_standard_tariff['Tariff-L4%'] = round(percent_change(merged_provider_standard_tariff['Amount'], merged_provider_standard_tariff['Level_4']), 2)
merged_provider_standard_tariff['Tariff-L5%'] = round(percent_change(merged_provider_standard_tariff['Amount'], merged_provider_standard_tariff['Level_5']), 2)

#Filter the dataframe for only certain categories and service frequency as shown below
merged_provider_standard_tariff = merged_provider_standard_tariff[
        (merged_provider_standard_tariff['Category'].isin(['CONSULTATIONS', 'INVESTIGATIONS', 'PROCEDURES', 'ROOMS AND FEEDING'])) &
        (merged_provider_standard_tariff['Frequency'].isin([5, 4, 3]))
    ]

#rename the description columns as below
merged_provider_standard_tariff.rename(columns = {'CPTDescription_x':'ProviderServiceDesc','CPTDescription_y':'StandardServiceDesc'}, inplace=True)
#ensure the two description columns are changed to upper case
merged_provider_standard_tariff['ProviderServiceDesc'] = merged_provider_standard_tariff['ProviderServiceDesc'].str.upper()
merged_provider_standard_tariff['StandardServiceDesc'] = merged_provider_standard_tariff['StandardServiceDesc'].str.upper()
#create a new column that uses the fuzzy function above to compare the 2 service description and assign a score
merged_provider_standard_tariff['Match_Score'] = merged_provider_standard_tariff.apply(lambda row: compare_cpt_description(row['ProviderServiceDesc'], row['StandardServiceDesc']), axis=1)
#select required columns as selected below
merged_provider_standard_tariff = merged_provider_standard_tariff[['ProviderClass', 'ProviderName', 'Category', 'CPTCode', 'ProviderServiceDesc','StandardServiceDesc',
                                                                        'Match_Score','Frequency', 'Amount', 'Level_1', 'Level_2', 'Level_3', 'Level_4', 'Level_5',
                                                                          'Tariff-L1%', 'Tariff-L2%', 'Tariff-L3%', 'Tariff-L4%', 'Tariff-L5%']]

#function to aggregate the dataframe on a provider-by-provider basis
def aggregate_provider_tariff(providercategory, tariff_level):
    # Filter merged_provider_standard_tariff by based on the selected provider category
    combined_data = merged_provider_standard_tariff[merged_provider_standard_tariff['ProviderClass'] == providercategory].copy()
    #add a new column that calculates the %variance of the provider tariff using the percent_change function from the selected tariff_level
    combined_data['Variance'] = round(percent_change(combined_data['Amount'], combined_data[tariff_level]), 2)


    # Group  the combined data by 'ProviderName'
    grouped_data = combined_data.groupby(['ProviderName'])
    #calculate the average variance of each provider based on the service frequency with 5 and 4 which are termed as high frequency services using the lambda function
    df_cond1 = grouped_data.apply(lambda x: round(x[x['Frequency'].isin([5, 4])]['Variance'].mean(), 2)).reset_index(name='High_Frequency_Ave')
    df_L1_cond1 = grouped_data.apply(lambda x: round(x[x['Frequency'].isin([5, 4])]['Tariff-L1%'].mean(), 2)).reset_index(name='L1_cond1_ave')
    df_L2_cond1 = grouped_data.apply(lambda x: round(x[x['Frequency'].isin([5, 4])]['Tariff-L2%'].mean(), 2)).reset_index(name='L2_cond1_ave')
    df_L3_cond1 = grouped_data.apply(lambda x: round(x[x['Frequency'].isin([5, 4])]['Tariff-L3%'].mean(), 2)).reset_index(name='L3_cond1_ave')
    df_L4_cond1 = grouped_data.apply(lambda x: round(x[x['Frequency'].isin([5, 4])]['Tariff-L4%'].mean(), 2)).reset_index(name='L4_cond1_ave')
    df_L5_cond1 = grouped_data.apply(lambda x: round(x[x['Frequency'].isin([5, 4])]['Tariff-L5%'].mean(), 2)).reset_index(name='L5_cond1_ave')

    ##calculate the average variance of each provider based on the service frequency with 3 which are termed as mid frequency services using the lambda function
    df_cond2 = grouped_data.apply(lambda x: round(x[x['Frequency'] == 3]['Variance'].mean(), 2)).reset_index(name='Mid_Frequency_Ave')
    df_L1_cond2 = grouped_data.apply(lambda x: round(x[x['Frequency'] == 3]['Tariff-L1%'].mean(), 2)).reset_index(name='L1_cond2_ave')
    df_L2_cond2 = grouped_data.apply(lambda x: round(x[x['Frequency'] == 3]['Tariff-L2%'].mean(), 2)).reset_index(name='L2_cond2_ave')
    df_L3_cond2 = grouped_data.apply(lambda x: round(x[x['Frequency'] == 3]['Tariff-L3%'].mean(), 2)).reset_index(name='L3_cond2_ave')
    df_L4_cond2 = grouped_data.apply(lambda x: round(x[x['Frequency'] == 3]['Tariff-L4%'].mean(), 2)).reset_index(name='L4_cond2_ave')
    df_L5_cond2 = grouped_data.apply(lambda x: round(x[x['Frequency'] == 3]['Tariff-L5%'].mean(), 2)).reset_index(name='L5_cond2_ave')

    #Merge all the dataframes above containing the average %variance of each provider from the 5 different tariff levels based on the 2 different conditions
    combined_df = pd.merge(df_cond1, df_cond2, on='ProviderName')
    combined_df = pd.merge(combined_df,df_L1_cond1, on= 'ProviderName')
    combined_df = pd.merge(combined_df, df_L1_cond2, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L2_cond1, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L2_cond2, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L3_cond1, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L3_cond2, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L4_cond1, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L4_cond2, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L5_cond1, on='ProviderName')
    combined_df = pd.merge(combined_df, df_L5_cond2, on='ProviderName')

    # Handle null values in combined_df
    combined_df = combined_df.fillna(0)
    
    # function that makes the recommendation for each provider based on the defined logic in the conditional statement below
    def calculate_rec(row):
        if row['L1_cond1_ave'] <= 7.5 and row['L1_cond2_ave'] <= 15:
            return 'Level 1'
        elif row['L2_cond1_ave'] <= 7.5 and row['L2_cond2_ave'] <= 15:
            return 'Level 2'
        elif row['L3_cond1_ave'] <= 7.5 and row['L3_cond2_ave'] <= 15:
            return 'Level 3'
        elif row['L4_cond1_ave'] <= 7.5 and row['L4_cond2_ave'] <= 15:
            return 'Level 4'
        elif row['L5_cond1_ave'] <= 100 and row['L5_cond2_ave'] <= 100:
            return 'Level 5'
        else:
            return 'BUPA Level'

    #create a new column in the combined_df by applying the function above for each provider
    combined_df['Recommendation'] = combined_df.apply(calculate_rec, axis=1)

    #return only the selected columns below
    combined_df = combined_df[['ProviderName', 'High_Frequency_Ave', 'Mid_Frequency_Ave', 'Recommendation']]

    return combined_df

# This is a new function that calculates the %variance for each selected provider and returns a dataframe with the variance from each level based on the 2 different conditions
#The function also returns the recommendation for the selected provider
def calculate_rec(df):
    #calculates the average variance of the selected provider based on the first condition(frequency 5 and 4)
    L1_cond1_ave = round(df[df['Frequency'].isin([5,4])]['Tariff-L1%'].mean(),2)
    L2_cond1_ave = round(df[df['Frequency'].isin([5,4])]['Tariff-L2%'].mean(),2)
    L3_cond1_ave = round(df[df['Frequency'].isin([5,4])]['Tariff-L3%'].mean(),2)
    L4_cond1_ave = round(df[df['Frequency'].isin([5,4])]['Tariff-L4%'].mean(),2)
    L5_cond1_ave = round(df[df['Frequency'].isin([5,4])]['Tariff-L5%'].mean(),2)
    #calculates the average variance of the selected provider based on the second condition(frequency 3)
    L1_cond2_ave = round(df[df['Frequency'] == 3]['Tariff-L1%'].mean(),2)
    L2_cond2_ave = round(df[df['Frequency'] == 3]['Tariff-L2%'].mean(),2)
    L3_cond2_ave = round(df[df['Frequency'] == 3]['Tariff-L3%'].mean(),2)
    L4_cond2_ave = round(df[df['Frequency'] == 3]['Tariff-L4%'].mean(),2)
    L5_cond2_ave = round(df[df['Frequency'] == 3]['Tariff-L5%'].mean(),2)
    #create a new dataframe using all the variables above
    data = {
    'Condition': ['Condition 1', 'Condition 2'],
    'Frequency': ['High', 'Mid'],
    'Level 1 Variance': [L1_cond1_ave, L1_cond2_ave],
    'Level 2 Variance': [L2_cond1_ave, L2_cond2_ave],
    'Level 3 Variance': [L3_cond1_ave, L3_cond2_ave],
    'Level 4 Variance': [L4_cond1_ave, L4_cond2_ave],
    'Level 5 Variance': [L5_cond1_ave, L5_cond2_ave]
    }
    #change the data above to a pandas df and assign to a variable
    table_df = pd.DataFrame(data)

    #write all the possible recommendations based on the results above and assign each recommendation to a variable
    rec1 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {L1_cond1_ave}% and {L1_cond2_ave}% from Standard LEVEL 1 Tariff respectively and is hereby recommended to TARIFF LEVEL 1'
    rec2 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {L2_cond1_ave}% and {L2_cond2_ave}% from Standard LEVEL 2 Tariff respectively and is hereby recommended to TARIFF LEVEL 2'
    rec3 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {L3_cond1_ave}% and {L3_cond2_ave}% from Standard LEVEL 3 Tariff respectively and is hereby recommended to TARIFF LEVEL 3'
    rec4 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {L4_cond1_ave}% and {L4_cond2_ave}% from Standard LEVEL 4 Tariff respectively and is hereby recommended to TARIFF LEVEL 4'
    rec5 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {L5_cond1_ave}% and {L5_cond2_ave}% from Standard LEVEL 5 Tariff respectively and is hereby recommended to TARIFF LEVEL 5'
    rec6 = f'The Service Tariff of {provider} for high frequency and mid frequency services has a variance of {L5_cond1_ave}% and {L5_cond2_ave}% from Standard LEVEL 5 Tariff respectively and is hereby recommended to BUPA LEVEL'
    
    #a loop to assign a recommendation to each selected provider based on our logic and return the variance dataframe and recommendation.
    if L1_cond1_ave <= 7.5 and L1_cond2_ave <= 15:
        return table_df, rec1
    elif L2_cond1_ave <= 7.5 and L2_cond2_ave <= 15:
        return table_df, rec2
    elif L3_cond1_ave <= 7.5 and L3_cond2_ave <= 15:
        return table_df, rec3
    elif L4_cond1_ave <= 7.5 and L4_cond2_ave <= 15:
        return table_df, rec4
    elif L5_cond1_ave <= 100 and L5_cond2_ave <= 100:
        return table_df, rec5
    else:
        return table_df, rec6

#apply the aggregate_provider_tariff function above to each category of providers and create a new column in the returned dataframe to indicate the provider category on TOSHFA
basic_providers_df = aggregate_provider_tariff('BASIC', 'Level_1')
basic_providers_df['TOSHFA Level'] = 'BASIC'
plus_providers_df = aggregate_provider_tariff('PLUS', 'Level_2')
plus_providers_df['TOSHFA Level'] = 'PLUS'
premium_providers_df = aggregate_provider_tariff('PREMIUM', 'Level_3')
premium_providers_df['TOSHFA Level'] = 'PREMIUM'
prestige_providers_df = aggregate_provider_tariff('PRESTIGE', 'Level_4')
prestige_providers_df['TOSHFA Level'] = 'PRESTIGE'
e_prestige_providers_df = aggregate_provider_tariff('INTERNATIONAL', 'Level_5')
e_prestige_providers_df['TOSHFA Level'] = 'INTERNATIONAL'
#combine all the providers in the different categories above to get a list with all the providers
all_providers_df = pd.concat([basic_providers_df,plus_providers_df,premium_providers_df,prestige_providers_df,e_prestige_providers_df], axis=0)
all_providers_df = all_providers_df[['ProviderName', 'TOSHFA Level', 'Recommendation']]

#this function adds a filter to the sidebar to enable us filter the final displayed categorisation by the model based on their recommended tariff level
def display_data(df):
    tariff_level = st.sidebar.selectbox(label='Select Tariff Level', options=['All', 'Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5', 'BUPA Level'])
    if tariff_level == 'All':
        data = df
    elif tariff_level == 'Level 1':
        data = df[df['Recommendation'] == 'Level 1'].reset_index(drop=True)
    elif tariff_level == 'Level 2':
        data = df[df['Recommendation'] == 'Level 2'].reset_index(drop=True)
    elif tariff_level == 'Level 3':
        data = df[df['Recommendation'] == 'Level 3'].reset_index(drop=True)
    elif tariff_level == 'Level 4':
        data = df[df['Recommendation'] == 'Level 4'].reset_index(drop=True)
    elif tariff_level == 'Level 5':
        data = df[df['Recommendation'] == 'Level 5'].reset_index(drop=True)
    elif tariff_level == 'BUPA Level':
        data = df[df['Recommendation'] == 'BUPA Level'].reset_index(drop=True)
    return data

# Define a function to apply custom styling
def highlight_columns(val, column_names, color):
    if val.name in column_names:
        return f'background-color: {color}'
    return ''

#add a radio button to select the task to be carried out
select_task = st.sidebar.radio('Select Task', options=['Check Provider CPT Mapping Compliance', 'Check Provider Classification'])

#below is the set of instructions to be executed when the first option is selected
if select_task == 'Check Provider CPT Mapping Compliance':
    st.title('CPTCode Mapping Compliance Tracker')
    #merge the provider tariff table with the standard cpt code and description master sheet and join on the CPTcode column
    provider_mapped_df = pd.merge(merged_provider_tariff, service_details, on=['CPTCode'], how='inner', indicator='Exist')
    #rename the CPTDescription column to ProviderDescription
    provider_mapped_df.rename(columns={'CPTDescription':'ProviderDescription'}, inplace=True)
    #change the provider description column to upper case to enhance comparison
    provider_mapped_df['ProviderDescription'] = provider_mapped_df['ProviderDescription'].str.upper()
    #create a list of unique providers and assign to a variable
    unq_provider = provider_mapped_df['ProviderName'].unique()
    #create a select box with the unique providers and assign the selected provider to a variable
    select_provider = st.sidebar.selectbox('Select Provider', options=unq_provider)
    #create a seperate dataframe for all services relating to a selected provider
    select_provider_df = provider_mapped_df[provider_mapped_df['ProviderName'] == select_provider]
    #create a new column using the fuzzy score function above to assign a score to each service based on their compatibility
    select_provider_df['Compatibility_Score'] = select_provider_df.apply(lambda row: compare_cpt_description(row['ProviderDescription'], row['StandardDescription']), axis=1)
    #select the columns to be displayed and reset the index
    select_provider_df = select_provider_df[['CPTCode', 'ProviderDescription', 'StandardDescription','Compatibility_Score', 'Amount']].reset_index(drop=True)
    #calculate the average compatibility score for the selected provider
    avg_compatibility_score = round(select_provider_df['Compatibility_Score'].mean(),2)
    #display a header for the title of the displayed table
    st.subheader(f'{select_provider} CPT Code Mapping with AVON Standard Service Description and TARIFF')
    #display the selected data to the portal
    st.write(select_provider_df)
    #add a download button to download the dataframe to excel
    st.download_button(
                label=f'Download {select_provider} tariff data as Excel File',
                data=select_provider_df.to_csv().encode('utf-8'),
                file_name=f'{select_provider} CPT Compatibility data.csv',
                mime='text/csv',
                )

    #display the average compatibility score to the portal
    st.subheader(f'The Average Compatibility Score of {select_provider} Service Description with AVON Standard Service Description is {avg_compatibility_score}%')

#set of instructions to be executed when the other task is selected.
elif select_task == 'Check Provider Classification':
    #adds a selectbox in the sidebar to enable users select different Provider Class
    provider_class = st.sidebar.selectbox(label='Select Provider Class', options=['ALL','BASIC', 'PLUS', 'PREMIUM', 'PRESTIGE', 'EXECUTIVE PRESTIGE'])

    #set of instructions to be executed when ALL is selected
    if provider_class == 'ALL':
        #apply the display_data function to display the categorization for all providers
        provider_df = display_data(all_providers_df)
        #aggregate the resulting df by the number of providers recommended to each tariff level
        level_agg = provider_df.groupby('Recommendation').agg(ProviderCount = ('Recommendation','count')).reset_index().sort_values(by='Recommendation', ascending=False)
        #aggregate the resulting df by the number of providers in each TOSHFA provider class
        toshfa_agg = provider_df.groupby('TOSHFA Level').agg(ProviderCount = ('TOSHFA Level', 'count')).reset_index().sort_values(by='TOSHFA Level', ascending=False)
        #get a list of unique providers in the dataframe
        unique_providers = merged_provider_standard_tariff['ProviderName'].unique()
        #use the unique providers above to create a selectbox that enables users to select a provider and assign it to a variable
        provider = st.sidebar.selectbox(label= 'Select Provider', options=unique_providers)
        #dispay a header for the aggregated recommendation count table
        st.subheader('Summary of Recommended Level and Count of Providers')
        st.dataframe(level_agg)
        st.dataframe(toshfa_agg)
        #display a header for the table containing the recommendation for all providers
        st.subheader('Recommended Tariff Level for ALL Providers')
        st.dataframe(provider_df)
        #filter the merged dataframe to return only services for selected provider
        selected_provider_df = merged_provider_standard_tariff[merged_provider_standard_tariff['ProviderName'] == provider].reset_index(drop=True)
        #return only certain columns as selected below
        selected_provider_df = selected_provider_df[['Category', 'CPTCode', 'ProviderServiceDesc','StandardServiceDesc','Match_Score','Frequency','Amount',
                                                    'Level_1','Tariff-L1%','Level_2','Tariff-L2%','Level_3',
                                                    'Tariff-L3%','Level_4','Tariff-L4%','Level_5','Tariff-L5%']]
        #apply the calculate_rec function to return the variance from each level and the corresponding recommendation and assign to a variable as below
        var_df, rec = calculate_rec(selected_provider_df)
        #display a title for the provider data and display the data for the selected provider
        st.subheader(f'Service Tariff Table for {provider}')
        st.dataframe(selected_provider_df)
        #display a title for the variance table and display the table for the selected provider
        st.subheader(f'{provider} Service Tariff Variance from each Standard Tariff Level')
        st.dataframe(var_df)
        #display a title for the recommendation and the display the result below it
        st.header('RECOMMENDATION')
        st.write(rec)
    #set of instructions to be executed when BASIC is selected. kindly refer to similar steps in the ALL loop above for comments for each steps
    if provider_class == 'BASIC':
        provider_df = display_data(basic_providers_df)
        level_agg = provider_df.groupby('Recommendation').agg(ProviderCount = ('Recommendation','count')).reset_index().sort_values(by='Recommendation', ascending=False)
        unique_providers = merged_provider_standard_tariff.loc[merged_provider_standard_tariff['ProviderClass'] == 'BASIC', 'ProviderName'].unique()
        provider = st.sidebar.selectbox(label= 'Select Provider', options=unique_providers)
        st.subheader('Summary of Recommended Level and Count of Providers')
        st.dataframe(level_agg)
        st.subheader('Recommended Tariff Level for BASIC Providers')
        st.dataframe(provider_df)

        selected_provider_df = merged_provider_standard_tariff[merged_provider_standard_tariff['ProviderName'] == provider].reset_index(drop=True)
        selected_provider_df = selected_provider_df[['Category', 'CPTCode', 'ProviderServiceDesc','StandardServiceDesc','Match_Score','Frequency','Amount',
                                                    'Level_1','Tariff-L1%','Level_2','Tariff-L2%','Level_3',
                                                    'Tariff-L3%','Level_4','Tariff-L4%','Level_5','Tariff-L5%']]
        var_df, rec = calculate_rec(selected_provider_df)
        st.subheader(f'Service Tariff Table for {provider}')
        st.dataframe(selected_provider_df)
        st.subheader(f'{provider} Service Tariff Variance from each Standard Tariff Level')
        st.dataframe(var_df)
        st.header('RECOMMENDATION')
        st.write(rec)
    #set of instructions to be executed when PLUS is selected. kindly refer to similar steps in the ALL loop above for comments for each steps
    elif provider_class == 'PLUS':
        provider_df = display_data(plus_providers_df)
        level_agg = provider_df.groupby('Recommendation').agg(ProviderCount = ('Recommendation','count')).reset_index().sort_values(by='Recommendation', ascending=False)
        unique_providers = merged_provider_standard_tariff.loc[merged_provider_standard_tariff['ProviderClass'] == 'PLUS', 'ProviderName'].unique()
        provider = st.sidebar.selectbox(label= 'Select Provider', options=unique_providers)
        st.subheader('Summary of Recommended Level and Count of Providers')
        st.dataframe(level_agg)
        st.subheader('Recommended Tariff Level for PLUS Providers')
        st.dataframe(provider_df)

        selected_provider_df = merged_provider_standard_tariff[merged_provider_standard_tariff['ProviderName'] == provider].reset_index(drop=True)
        selected_provider_df = selected_provider_df[['Category', 'CPTCode', 'ProviderServiceDesc','StandardServiceDesc','Match_Score', 'Frequency','Amount',
                                                    'Level_1','Tariff-L1%','Level_2','Tariff-L2%','Level_3',
                                                    'Tariff-L3%','Level_4','Tariff-L4%','Level_5','Tariff-L5%']]
        var_df, rec = calculate_rec(selected_provider_df)
        st.subheader(f'Service Tariff Table for {provider}')
        st.dataframe(selected_provider_df)
        st.subheader(f'{provider} Service Tariff Variance from each Standard Tariff Level')
        st.dataframe(var_df)
        st.header('RECOMMENDATION')
        st.write(rec)
        
    #set of instructions to be executed when PREMIUM is selected. kindly refer to similar steps in the ALL loop above for comments for each steps
    elif provider_class == 'PREMIUM':
        provider_df = display_data(premium_providers_df)
        level_agg = provider_df.groupby('Recommendation').agg(ProviderCount = ('Recommendation','count')).reset_index().sort_values(by='Recommendation', ascending=False)
        unique_providers = merged_provider_standard_tariff.loc[merged_provider_standard_tariff['ProviderClass'] == 'PREMIUM', 'ProviderName'].unique()
        provider = st.sidebar.selectbox(label= 'Select Provider', options=unique_providers)
        st.subheader('Summary of Recommended Level and Count of Providers')
        st.dataframe(level_agg)
        st.subheader('Recommended Tariff Level for PREMIUM Providers')
        st.dataframe(provider_df)

        selected_provider_df = merged_provider_standard_tariff[merged_provider_standard_tariff['ProviderName'] == provider].reset_index(drop=True)
        selected_provider_df = selected_provider_df[['Category', 'CPTCode', 'ProviderServiceDesc','StandardServiceDesc','Match_Score', 'Frequency','Amount',
                                                    'Level_1','Tariff-L1%','Level_2','Tariff-L2%','Level_3',
                                                    'Tariff-L3%','Level_4','Tariff-L4%','Level_5','Tariff-L5%']]
        var_df, rec = calculate_rec(selected_provider_df)
        st.subheader(f'Service Tariff Table for {provider}')
        st.dataframe(selected_provider_df)
        st.subheader(f'{provider} Service Tariff Variance from each Standard Tariff Level')
        st.dataframe(var_df)
        st.header('RECOMMENDATION')
        st.write(rec)
    #set of instructions to be executed when PRESTIGE is selected. kindly refer to similar steps in the ALL loop above for comments for each steps
    elif provider_class == 'PRESTIGE':
        provider_df = display_data(prestige_providers_df)
        level_agg = provider_df.groupby('Recommendation').agg(ProviderCount = ('Recommendation','count')).reset_index().sort_values(by='Recommendation', ascending=False)
        unique_providers = merged_provider_standard_tariff.loc[merged_provider_standard_tariff['ProviderClass'] == 'PRESTIGE', 'ProviderName'].unique()
        provider = st.sidebar.selectbox(label= 'Select Provider', options=unique_providers)
        st.subheader('Summary of Recommended Level and Count of Providers')
        st.dataframe(level_agg)
        st.subheader('Recommended Tariff Level for PRESTIGE Providers')
        st.dataframe(provider_df)

        selected_provider_df = merged_provider_standard_tariff[merged_provider_standard_tariff['ProviderName'] == provider].reset_index(drop=True)
        selected_provider_df = selected_provider_df[['Category', 'CPTCode', 'ProviderServiceDesc','StandardServiceDesc','Match_Score', 'Frequency','Amount',
                                                    'Level_1','Tariff-L1%','Level_2','Tariff-L2%','Level_3',
                                                    'Tariff-L3%','Level_4','Tariff-L4%','Level_5','Tariff-L5%']]
        var_df, rec = calculate_rec(selected_provider_df)
        st.subheader(f'Service Tariff Table for {provider}')
        st.dataframe(selected_provider_df)
        st.subheader(f'{provider} Service Tariff Variance from each Standard Tariff Level')
        st.dataframe(var_df)
        st.header('RECOMMENDATION')
        st.write(rec)
        # st.write(provider_data)
        
    #set of instructions to be executed when EXECUTIVE PRESTIGE is selected. kindly refer to similar steps in the ALL loop above for comments for each steps
    elif provider_class == 'EXECUTIVE PRESTIGE':
        provider_df = display_data(e_prestige_providers_df)
        level_agg = provider_df.groupby('Recommendation').agg(ProviderCount = ('Recommendation','count')).reset_index().sort_values(by='Recommendation', ascending=False)
        unique_providers = merged_provider_standard_tariff.loc[merged_provider_standard_tariff['ProviderClass'] == 'INTERNATIONAL', 'ProviderName'].unique()
        provider = st.sidebar.selectbox(label= 'Select Provider', options=unique_providers)
        st.subheader('Summary of Recommended Level and Count of Providers')
        st.dataframe(level_agg)
        st.subheader('Recommended Tariff Level for INTERNATIONAL Providers')
        st.dataframe(provider_df)

        selected_provider_df = merged_provider_standard_tariff[merged_provider_standard_tariff['ProviderName'] == provider].reset_index(drop=True)
        selected_provider_df = selected_provider_df[['Category', 'CPTCode', 'ProviderServiceDesc','StandardServiceDesc','Match_Score', 'Frequency','Amount',
                                                    'Level_1','Tariff-L1%','Level_2','Tariff-L2%','Level_3',
                                                    'Tariff-L3%','Level_4','Tariff-L4%','Level_5','Tariff-L5%']]
        var_df, rec = calculate_rec(selected_provider_df)
        st.subheader(f'Service Tariff Table for {provider}')
        st.dataframe(selected_provider_df)
        st.subheader(f'{provider} Service Tariff Variance from each Standard Tariff Level')
        st.dataframe(var_df)
        st.header('RECOMMENDATION')
        st.write(rec)
    
    #add a download button to enable download of the selected provider tariff data
    st.download_button(
                label=f'Download {provider} tariff data as Excel File',
                data=selected_provider_df.to_csv().encode('utf-8'),
                file_name=f'{provider} tariff data.csv',
                mime='text/csv',
                )
    #add a download button to enable download of the selected provider class classification
    st.download_button(
                label=f'Download {provider_class} tariff Classification as Excel File',
                data=provider_df.to_csv().encode('utf-8'),
                file_name=f'{provider_class} Providers Tariff Classification.csv',
                mime='text/csv',
                )
    

# # Specify the columns and the color you want to highlight
# highlight_columns_names = ['Age', 'Score']
# highlight_color = 'yellow'

# # Apply the styling using the Styler object
# styled_df = df.style.apply(highlight_columns, column_names=highlight_columns_names, color=highlight_color, axis=None)