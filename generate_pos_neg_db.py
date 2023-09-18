#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: saedasa
"""

import os
import pandas as pd
import datetime
import numpy as np
import cdflib
import math

def round_to_nearest_quarter_hour(timestamp):
    timestamp_rounded = timestamp - datetime.timedelta(minutes=timestamp.minute % 15,
                                                      seconds=timestamp.second,
                                                      microseconds=timestamp.microsecond)
    if timestamp.minute >= 45:
        timestamp_rounded += datetime.timedelta(hours=1)
    return timestamp_rounded

def check_file_exists(timestamp):
    main_path=''
    flag=True
    for i in np.arange(0.25,24.25,0.25):
        time_change = datetime.timedelta(hours=-1*i)
        newTime=timestamp+time_change
        year2 = str(newTime.year)
        month2 = str(newTime.month).zfill(2)
        day2 = str(newTime.day).zfill(2)
        filename2 = f"gps_tec15min_igs_{year2}{month2}{day2}_v01.cdf"
        filepath2 = os.path.join(main_path, year2, filename2)
        flag=flag & os.path.exists(filepath2) 
    return int(flag)

def get_files_names(timestamp):
    fnames=[]
    main_path=''
    for i in np.arange(0.25,24.25,0.25):
        time_change = datetime.timedelta(hours=-1*i)
        newTime=timestamp+time_change
        year = str(newTime.year)
        month = str(newTime.month).zfill(2)
        day = str(newTime.day).zfill(2)
        filename = f"gps_tec15min_igs_{year}{month}{day}_v01.cdf"
        filepath = os.path.join(main_path, year, filename)
        fnames.append(filepath)
    return fnames

def get_maps_indicies(timestamp):
    maps_indicies=[]
    for i in np.arange(0.25,24.25,0.25):
        time_change = datetime.timedelta(hours=-1*i)
        newTime=timestamp+time_change
        Hour=newTime.hour+newTime.minute/60;
        MapNumber= math.floor(Hour*60/15);
        maps_indicies.append(MapNumber)
    return maps_indicies


def get_negatives_files_names(timestamp):
    fnames={}
    rng=np.arange(1998,2021)
    rng=rng[rng != timestamp.year]
    for year_val in rng:
        newTime=timestamp.replace(year=year_val)
        if(check_file_exists(newTime)):
            fnames[year_val]=get_files_names(newTime)

            
    return fnames



# function to get positive maps from cdf files
def get_positive_maps(row):
    positive_maps = []
    lat = row['latitude']
    lon = row['longitude']
    radius = 1
    for i, file_path in enumerate(row['files_names']):
        with cdflib.CDF(file_path) as cdf:
            data = cdf.varget('tecUQR')[row['maps_indicies'][i]]
            
            positive_maps.append(data)
    return positive_maps


def is_valid_ssn(date_pos, date_neg):
    from datetime import datetime
    ssn_neg = solar_cycles.query( f'time== "{date_neg}"').ssn
    ssn_neg=ssn_neg.iloc[0]
    ssn_pos = solar_cycles.query( f'time== "{date_pos}"').ssn
    ssn_pos=ssn_pos.iloc[0]
    return (ssn_neg<=50 and ssn_pos<=50)

def is_solar_flare(given_date):
    s_flares_path=''
    from datetime import datetime, timedelta
    solar_flares=pd.read_csv(s_flares_path)
    solar_flares['Datetime'] = pd.to_datetime(solar_flares[['Year', 'Month', 'Day']])
    three_days_before = [given_date - pd.DateOffset(days=x) for x in range(3)]
    mask = solar_flares['Datetime'].isin(three_days_before + [given_date])
    result = solar_flares.loc[mask]
    return len(result)!=0




def getTECVal(tecMap,location,radius):
    lat=location[0]
    lon=location[1]
    Lats = np.arange(87.5,-90,-2.5)
    Longs = np.arange(-180,185,5)
    diffLats=np.abs(Lats-lat)
    diffLongs=np.abs(Longs-lon)
    ClosestLongs=Longs[diffLongs<=5*radius]
    ClosestLats=Lats[diffLats<=2.5*radius]
    Weights=[]
    Neighbours=[]
    for i in range(len(ClosestLongs)):
        for j in range(len(ClosestLats)):
            latIndx=(87.5-ClosestLats[j])/2.5
            longIndx=(180+ClosestLongs[i])/5
            Currdist = np.sqrt((ClosestLats[j]-lat)**2+(ClosestLongs[i]-lon)**2)
            Neighbours.append(tecMap[int(latIndx),int(longIndx)])
            Weights.append(1/Currdist)
    Weights=np.array(Weights)
    Neighbours=np.array(Neighbours)
    val = np.average(Neighbours, weights=Weights)
    return val


def get_tec_time_series_pos(row):
    vtec_values_positive = [] 
    sample_location=[row.latitude, row.longitude]
    radius  = 1
    for i in range(96):
        pos_map = row.positive_maps[i]
        pos_res = getTECVal(pos_map, sample_location, radius)
        vtec_values_positive.append(pos_res)
    return vtec_values_positive

def get_tec_time_series_neg(row, negative_maps):
    vtec_values_negative = [] 
    sample_location=[row.latitude, row.longitude]
    radius  = 1
    for i in range(96):
        neg_map = negative_maps[i]
        neg_res = getTECVal(neg_map, sample_location, radius)
        vtec_values_negative.append(neg_res)
    return vtec_values_negative



# function to get negative maps from randomly picked cdf files

def get_negative_maps(row, pos_row):
    from datetime import datetime, timedelta
    import random
    negative_maps = []
    day_month = (row['full_time'].month, row['full_time'].day)
    years=list(row['negatives_files'].keys())
    date_pos = datetime(year=row['full_time'].year, month=day_month[0], day=1)
    dates_list = []
    for year in years:
        new_date = datetime(year=year, month=day_month[0], day=day_month[1])
        dates_list.append(new_date)
    candidates = [x for x in dates_list if is_solar_flare(x)==False and is_valid_ssn(date_pos, datetime(year=x.year, month=x.month, day=1))==True]
    # print(random.choice(range(len(candidates))))
    # print(candidates)
    if candidates:
        
        for cand in candidates:
            negative_maps = []
            index_of_picked_negative = list(row['negatives_files'].keys()).index(cand.year)
            negative_file_paths = list(row['negatives_files'].values())[index_of_picked_negative]
            for index in row['maps_indicies']:
                with cdflib.CDF(negative_file_paths[index_of_picked_negative]) as cdf:
                    data = cdf.varget('tecUQR')[index]#, starttime=0, count=1, sRecords=index, sArrays=0, sIndices=0)
                    negative_maps.append(data)
        
            neg_vals = get_tec_time_series_neg(row, negative_maps)    
            pos_row_lst = pos_row.tolist()
            result = all(x <= y for x, y in zip(neg_vals, pos_row_lst))
            if result == True:
                return neg_vals, cand
        return None, None
  

if __name__ == "__main__":
    full_db_path=''
    df = pd.read_csv(full_db_path)
    df['full_time'] = pd.to_datetime(df['full_time'])
    #round the time to the closest 15 min mutiple time
    df['full_time'] = df['full_time'].apply(round_to_nearest_quarter_hour)
    df['exists'] = df['full_time'].apply(check_file_exists)
    df_exists=df[(df['exists']==1)]

    
    solar_cycles = pd.read_json('observed-solar-cycle-indices.json')
    solar_cycles.drop(columns=['smoothed_ssn','observed_swpc_ssn','smoothed_swpc_ssn','f10.7','smoothed_f10.7'],inplace=True)
    solar_cycles.columns=['time','ssn']
    solar_cycles['time']=pd.to_datetime(solar_cycles['time'])


    df_exists['files_names'] = df['full_time'].apply(get_files_names)
    df_exists['maps_indicies'] = df['full_time'].apply(get_maps_indicies)
    df_exists['negatives_files'] = df_exists['full_time'].apply(get_negatives_files_names)
    mask = df_exists['negatives_files'].apply(len) > 0
    df_final = df_exists[mask]
    df_final=df_final[df_final['Sunspots']<50]
    ds_final_greater_than_6 = df_final[df_final['mag']>=6]
    ds_final_greater_than_6['positive_maps'] = ds_final_greater_than_6.apply(get_positive_maps, axis=1)
    ds_final_greater_than_6.index = pd.RangeIndex(len(ds_final_greater_than_6.index))
    ds_final_greater_than_6.index = pd.RangeIndex(len(ds_final_greater_than_6.index))
    time_seires_pos_df = ds_final_greater_than_6.apply(lambda row: pd.Series(get_tec_time_series_pos(row)), axis=1, result_type='expand')
    ds_final_greater_than_6[['negative_vals', 'date_of_picked_negative']] = ds_final_greater_than_6.apply(lambda row: pd.Series(get_negative_maps(row,time_seires_pos_df.iloc[row.name])), axis=1, result_type='expand')
    ds_final_greater_than_6.to_pickle('negative_maps_final_ssn_sf_2.pkl')
    print('Finished!!')

