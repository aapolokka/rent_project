import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


#Function to scrape vuokraovi rent listings based on the city name
def scrape_data(location):

    all_listings_data = []
    page_num = 1
    
    # web page to scrape
    url = 'https://www.vuokraovi.com/vuokra-asunnot/'+str(location)+'?page='+str(page_num)+'&pageType='
    page = requests.get(url)
    obj = BeautifulSoup(page.content, 'lxml')

    # number of listings pages on web page
    n_pages_l = []
    for i in obj.findAll('div',{'class':'list-pager'}):
        a_tag = i.findAll('a')[5].text
        n_pages_l.append(int(a_tag))

    n_pages=n_pages_l[0]

    # scrape the data
    while page_num <= n_pages:
        url = 'https://www.vuokraovi.com/vuokra-asunnot/'+str(location)+'?page='+str(page_num)+'&pageType='
        page = requests.get(url)
        obj = BeautifulSoup(page.content, 'lxml')

        if len(obj.findAll('div',{'class': 'list-item-container'})) == 0:
            break

        # scraped data into lists
        for data in obj.findAll('div',{'class': 'list-item-container'}):
            address = data.find('span', {'class':'address'}).text.replace(",", '').replace('\r','').replace('\n', '')
            price = data.find('span', {'class':'price'}).text.replace(u'\xa0', u'').replace('\n', '').replace('€/kk', '').replace(',', '.')
            type_size = data.find('li', {'class':'semi-bold'}).text.replace('m²', '')
            rooms = data.findAll('li', {'class':'semi-bold'})[1].text
            listing_data = [address, price, type_size, rooms]
            all_listings_data.append(listing_data)
        
        page_num += 1
    
    # pandas dataframe of the scraped data
    df = pd.DataFrame(all_listings_data, columns=['Address', 'Price', 'House Type', 'Info'])

    #df = modify_df(df)

    df.to_csv("rent_listings_"+location+".csv")

    return df


# function to estimate number of rooms if not given in listing 
def estimate_rooms(row, avg_size_per_room):
    if row['Rooms'] == '' or len(row['Rooms']) > 2:
        if round(row['Size (sqm)'] / avg_size_per_room) == 0:
            return 1
        else:
            return round(row['Size (sqm)'] / avg_size_per_room)
    else:
        return row['Rooms']


# function to modify and clean the data in dataframe
def modify_df(df, location):
    
    df[['City', 'District', 'Street']] = df['Address'].str.split('     ', expand=True, n=2)
    df.drop('Address', axis=1, inplace=True)
    df['City'] = df['City'].str.strip()
    df['District'] = df['District'].str.strip()
    df['Street'] = df['Street'].str.strip()
    
    df[['House Type', 'Size (sqm)']] = df['House Type'].str.split(', ', expand=True)
    df['Size (sqm)'] = df['Size (sqm)'].str.strip().str.replace(',', '.')
    df['Size (sqm)'].replace('', np.nan, inplace=True)
    df['Size (sqm)'] = df['Size (sqm)'].astype(float)
    df = df.dropna(subset=['Size (sqm)'])


    df.loc[:, 'Price (eur/kk)'] = df['Price'].str.strip().str.replace(' €/vko', '', regex=False)  
    mask = df['Price'].str.contains('€/vko')
    df.loc[mask, 'Price (eur/kk)'] = df.loc[mask, 'Price (eur/kk)'].astype(float) * 4 
    df.drop('Price', axis=1, inplace=True)

    split_info = df['Info'].str.split('[+,]', expand=True, n=1)
    
    df.loc[:, 'Rooms'] = split_info[0].str.strip().str.replace('[a-zA-ZöäåÖÄÅ]', '', regex=True)
    df.loc[:, 'Additional Info'] = split_info[1].str.strip().str.replace(',', '+').str.replace(' ', '')
    
    df.drop('Info', axis=1, inplace=True)
    
    valid_rooms = df[df['Rooms'].str.isnumeric()]
    avg_size_per_room = (valid_rooms['Size (sqm)'] / valid_rooms['Rooms'].astype(float)).mean()

    df.loc[:, 'Rooms'] = df.apply(lambda row: estimate_rooms(row, avg_size_per_room), axis=1)
    
    df = df.iloc[:, [1, 2, 3, 0, 4, 5, 6, 7]]

    df.to_csv("rent_listings_"+location+".csv")

    return df


def main():

    # top 10 cities of Finland
    listings_helsinki = modify_df(scrape_data('Helsinki'), 'Helsinki')
    listings_espoo = modify_df(scrape_data('Espoo'), 'Espoo')
    listings_tampere = modify_df(scrape_data('Tampere'), 'Tampere')
    listings_vantaa = modify_df(scrape_data('Vantaa'), 'Vantaa')
    listings_oulu = modify_df(scrape_data('Oulu'), 'Oulu')
    listings_turku = modify_df(scrape_data('Turku'), 'Turku')
    listings_jyvaskyla = modify_df(scrape_data('Jyväskylä'), 'Jyväskylä')
    listings_kuopio = modify_df(scrape_data('Kuopio'), 'Kuopio')
    listings_lahti = modify_df(scrape_data('Lahti'), 'Lahti')
    listings_pori = modify_df(scrape_data('Pori'), 'Pori')

    # one data frame of the top 10 cities in Finland
    data_frames = [listings_helsinki, listings_espoo, listings_tampere, listings_vantaa, listings_oulu, listings_turku, listings_jyvaskyla, listings_kuopio, listings_lahti, listings_pori]

    listings_top_ten = pd.concat(data_frames, ignore_index=True)

    
    listings_top_ten = listings_top_ten[pd.to_numeric(listings_top_ten['Price (eur/kk)'], errors='coerce').notna()]
    listings_top_ten = listings_top_ten[pd.to_numeric(listings_top_ten['Rooms'], errors='coerce').notna()]

    # remove all rows whit null value in column
    for index, row in listings_top_ten.iterrows():
        if row.isnull().any() or row.isin(['']).any():
            listings_top_ten = listings_top_ten.drop(index)

    listings_top_ten.to_csv("listings_top_ten_cities_finland.csv", index=True)


if __name__ == '__main__':
    main()
